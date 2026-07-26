"use client";

import { useEffect, useRef, useState } from "react";
import { conversations, streamChat } from "@/lib/api";
import { useChatStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";

interface ChatPanelProps {
  conversationId: string | null;
  onNewConversation: () => void;
}

interface Message {
  id: string;
  role: string;
  content: string;
  citations?: Array<{
    chunk_id: string;
    document_id: string;
    text: string;
    page_number?: number;
    score: number;
  }>;
  faithfulness_score?: number;
  created_at: string;
}

export function ChatPanel({ conversationId, onNewConversation }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { streamingContent, isStreaming, appendToken, setStreaming, resetStreaming } = useChatStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load messages when conversation changes
  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      return;
    }
    setLoading(true);
    conversations.messages(conversationId).then((res) => {
      setMessages(Array.isArray(res.data) ? res.data : []);
    }).catch(console.error).finally(() => setLoading(false));
  }, [conversationId]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    if (!conversationId) {
      onNewConversation();
      return;
    }

    const userMessage = input.trim();
    setInput("");
    setError(null);

    // Add user message locally
    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: userMessage,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    // Start streaming
    setStreaming(true);
    resetStreaming();

    streamChat(
      conversationId,
      userMessage,
      // onToken
      (token) => {
        appendToken(token);
      },
      // onDone
      (data) => {
        setStreaming(false);
        // Add assistant message
        const assistantMsg: Message = {
          id: data.message_id || `msg-${Date.now()}`,
          role: "assistant",
          content: data.content || streamingContent,
          citations: data.citations,
          faithfulness_score: data.faithfulness_score,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
        resetStreaming();
      },
      // onError
      (err) => {
        setStreaming(false);
        setError(err);
        resetStreaming();
      }
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCitationClick = (citation: any) => {
    // Dispatch custom event for document viewer to highlight
    window.dispatchEvent(
      new CustomEvent("citation-highlight", {
        detail: { chunkId: citation.chunk_id, documentId: citation.document_id },
      })
    );
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between">
        <h2 className="font-semibold text-sm text-foreground">Chat</h2>
        <button
          onClick={onNewConversation}
          className="text-xs text-veridoc-500 hover:text-veridoc-600 font-medium"
        >
          + New Chat
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !isStreaming && (
          <div className="h-full flex items-center justify-center">
            <div className="text-center max-w-xs">
              <div className="w-12 h-12 rounded-2xl bg-veridoc-100 mx-auto mb-3 flex items-center justify-center">
                <svg className="w-6 h-6 text-veridoc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <p className="text-sm text-muted-foreground">
                Ask a question about your documents
              </p>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              "flex",
              msg.role === "user" ? "justify-end" : "justify-start"
            )}
          >
            <div
              className={cn(
                "max-w-[85%] rounded-2xl px-4 py-3 text-sm",
                msg.role === "user"
                  ? "bg-veridoc-500 text-white rounded-br-md"
                  : "bg-secondary text-foreground rounded-bl-md"
              )}
            >
              {msg.role === "assistant" ? (
                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              ) : (
                <p>{msg.content}</p>
              )}

              {/* Citations */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-3 pt-2 border-t border-veridoc-200/30">
                  <p className="text-xs text-veridoc-200 mb-1.5 font-medium">Sources:</p>
                  <div className="flex flex-wrap gap-1">
                    {msg.citations.slice(0, 3).map((cit, i) => (
                      <button
                        key={i}
                        onClick={() => handleCitationClick(cit)}
                        className="citation-chip"
                      >
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M4 6h16M4 12h16m-7 6h7" />
                        </svg>
                        {cit.page_number ? `p.${cit.page_number}` : `src ${i + 1}`}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Faithfulness indicator */}
              {msg.faithfulness_score !== undefined && msg.faithfulness_score !== null && (
                <div className="mt-2 flex items-center gap-1.5">
                  <div className={cn(
                    "w-1.5 h-1.5 rounded-full",
                    msg.faithfulness_score >= 0.8 ? "bg-green-400" :
                    msg.faithfulness_score >= 0.5 ? "bg-amber-400" : "bg-red-400"
                  )} />
                  <span className="text-xs opacity-60">
                    {Math.round(msg.faithfulness_score * 100)}% faithful
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Streaming message */}
        {isStreaming && streamingContent && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-2xl px-4 py-3 text-sm bg-secondary text-foreground rounded-bl-md">
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown>{streamingContent}</ReactMarkdown>
              </div>
              <span className="streaming-cursor inline-block w-2 h-4" />
            </div>
          </div>
        )}

        {error && (
          <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
            Error: {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t bg-white">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={conversationId ? "Ask a question..." : "Start a new conversation..."}
            rows={1}
            className="flex-1 px-4 py-2.5 rounded-xl border border-input bg-secondary/50 resize-none
                       focus:outline-none focus:ring-2 focus:ring-veridoc-500/20 focus:border-veridoc-500
                       text-sm transition-all duration-150"
            style={{ minHeight: "40px", maxHeight: "120px" }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className={cn(
              "w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-150",
              "bg-veridoc-500 text-white hover:bg-veridoc-600",
              "disabled:opacity-30 disabled:cursor-not-allowed",
              "focus:outline-none focus:ring-2 focus:ring-veridoc-500/20"
            )}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
