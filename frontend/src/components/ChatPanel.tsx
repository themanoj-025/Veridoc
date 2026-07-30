"use client";

import { useEffect, useRef, useState } from "react";
import { conversations, streamChat } from "@/lib/api";
import { useChatStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { ThumbsUpDown } from "@/components/ThumbsUpDown";
import { OCRBadge } from "@/components/OCRBadge";
import type { Citation as CitationType } from "@/lib/api-types";
import ReactMarkdown from "react-markdown";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";

// Allowlist for citation chips rendered as inline HTML inside markdown.
// All other tags/attributes from LLM output are stripped.
// Export for reuse in sanitization tests — keep in sync!
export const sanitizeSchema = {
  ...defaultSchema,
  tagNames: [...(defaultSchema.tagNames || []), "button", "sup"],
  attributes: {
    ...defaultSchema.attributes,
    // NOTE: onClick is deliberately excluded — LLM-generated markdown
    // should never contain executable event handlers. Citation chips
    // are rendered by custom React components, not raw HTML.
    button: ["className", "type", "aria-label"],
    sup: ["className"],
    code: ["className"],
    span: ["className", "data-*"],
    div: ["className"],
    a: ["href", "target", "rel", "className", "aria-label"],
  },
};

interface ChatPanelProps {
  conversationId: string | null;
  onNewConversation: () => void;
}

// Use the generated MessageResponse for message data.
// We keep a local subset for temp messages before the API response comes back.
interface LocalMessage {
  id: string;
  role: string;
  content: string;
  citations?: CitationType[];
  faithfulness_score?: number;
  model_used?: string | null;
  fallback_used?: boolean;
  created_at: string;
}

type Message = LocalMessage;

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

    const chatCtrl = streamChat({
      conversationId,
      message: userMessage,
      onToken: (token) => {
        appendToken(token);
      },
      onDone: (data) => {
        setStreaming(false);
        // Add assistant message
        const assistantMsg: Message = {
          id: data.message_id || `msg-${Date.now()}`,
          role: "assistant",
          content: data.content || streamingContent,
          citations: data.citations,
          faithfulness_score: data.faithfulness_score,
          model_used: data.model_used,
          fallback_used: data.fallback_used,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
        resetStreaming();
      },
      onError: (err) => {
        setStreaming(false);
        setError(err);
        resetStreaming();
      },
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCitationClick = (citation: any) => {
    // Dispatch navigation event: dashboard listens to switch to viewer tab
    window.dispatchEvent(
      new CustomEvent("citation-navigate", {
        detail: { documentId: citation.document_id },
      })
    );
    // Dispatch highlight event: DocumentViewer scrolls to the chunk
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

        {messages.map((msg, idx) => (
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
                  <ReactMarkdown rehypePlugins={[[rehypeSanitize, sanitizeSchema]]}>
                    {msg.content}
                  </ReactMarkdown>
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
                        <OCRBadge ocrUsed={cit.ocr_used ?? false} size="xs" />
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Model + Faithfulness + Fallback indicators */}
              <div className="mt-2 flex items-center gap-2 flex-wrap">
                {msg.fallback_used && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 font-medium">
                    ⚠️ Answered via fallback model
                  </span>
                )}
                {msg.model_used && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-mono">
                    {msg.model_used.includes("ollama") ? "🖥️ " : "☁️ "}
                    {msg.model_used}
                  </span>
                )}
                {msg.faithfulness_score !== undefined && msg.faithfulness_score !== null && (
                  <span className="flex items-center gap-1">
                    <div className={cn(
                      "w-1.5 h-1.5 rounded-full",
                      msg.faithfulness_score >= 0.8 ? "bg-green-400" :
                      msg.faithfulness_score >= 0.5 ? "bg-amber-400" : "bg-red-400"
                    )} />
                    <span className="text-[10px] text-muted-foreground">
                      {Math.round(msg.faithfulness_score * 100)}% faithful
                    </span>
                  </span>
                )}
              </div>

              {/* Thumbs-up/down feedback */}
              {msg.role === "assistant" && conversationId && (
                <ThumbsUpDown
                  messageId={msg.id}
                  conversationId={conversationId}
                  question={messages[idx - 1]?.content || ""}
                  answer={msg.content}
                  citations={msg.citations}
                  faithfulnessScore={msg.faithfulness_score}
                />
              )}
            </div>
          </div>
        ))}

        {/* Streaming message */}
        {isStreaming && streamingContent && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-2xl px-4 py-3 text-sm bg-secondary text-foreground rounded-bl-md">
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown rehypePlugins={[[rehypeSanitize, sanitizeSchema]]}>
                  {streamingContent}
                </ReactMarkdown>
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
