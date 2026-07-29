"use client";

import { cn } from "@/lib/utils";
import { formatFileSize, truncate } from "@/lib/utils";
import type { DocumentResponse, ConversationResponse } from "@/lib/api-types";

// Use generated types from the API schema
type Document = DocumentResponse;
type Conversation = ConversationResponse;

interface DocumentListProps {
  documents: Document[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onUpload: () => void;
  onNewChat: () => void;
  selectedConversationId: string | null;
  conversations: Conversation[];
  onSelectConversation: (id: string) => void;
  loading?: boolean;
}

import { DocumentListSkeleton, ConversationListSkeleton } from "@/components/Skeleton";

export function DocumentList({
  documents,
  selectedId,
  onSelect,
  onUpload,
  onNewChat,
  selectedConversationId,
  conversations,
  onSelectConversation,
  loading = false,
}: DocumentListProps) {
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b">
        <h2 className="font-semibold text-sm text-foreground mb-3">Documents</h2>
        <button
          onClick={onUpload}
          className="w-full py-2 px-3 rounded-lg bg-veridoc-500 text-white text-sm font-medium
                     hover:bg-veridoc-600 transition-colors flex items-center justify-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Upload Document
        </button>
      </div>

      {/* Document list */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <DocumentListSkeleton />
        ) : documents.length === 0 ? (
          <div className="p-6 text-center">
            <div className="w-12 h-12 rounded-full bg-veridoc-100 mx-auto mb-3 flex items-center justify-center">
              <svg className="w-6 h-6 text-veridoc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
            </div>
            <p className="text-sm text-muted-foreground">No documents yet</p>
            <p className="text-xs text-muted-foreground mt-1">Upload a PDF, DOCX, or TXT file to get started</p>
          </div>
        ) : (
          <div className="p-2 space-y-1">
            {documents.map((doc) => (
              <button
                key={doc.id}
                onClick={() => onSelect(doc.id)}
                className={cn(
                  "w-full text-left p-3 rounded-xl transition-all duration-150",
                  "hover:bg-secondary group",
                  selectedId === doc.id && "bg-veridoc-50 ring-1 ring-veridoc-200"
                )}
              >
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-veridoc-100 flex items-center justify-center shrink-0">
                    <svg className="w-4 h-4 text-veridoc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground truncate">
                      {doc.title}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {formatFileSize(doc.file_size)} · {doc.file_type.toUpperCase()}
                    </p>
                    <p className="text-xs text-muted-foreground/60 mt-0.5">
                      {doc.status === "indexed" ? (
                        <span className="text-green-600">Indexed</span>
                      ) : doc.status === "failed" ? (
                        <span className="text-red-600">Failed</span>
                      ) : (
                        <span className="text-amber-600">{doc.status}</span>
                      )}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Conversations */}
      <div className="border-t">
        <div className="p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-sm text-foreground">Conversations</h2>
            <button
              onClick={onNewChat}
              className="text-xs text-veridoc-500 hover:text-veridoc-600 font-medium"
            >
              + New
            </button>
          </div>
          {loading ? (
            <ConversationListSkeleton />
          ) : conversations.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-2">
              No conversations yet
            </p>
          ) : (
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => onSelectConversation(conv.id)}
                  className={cn(
                    "w-full text-left p-2 rounded-lg transition-colors text-sm",
                    "hover:bg-secondary",
                    selectedConversationId === conv.id && "bg-veridoc-50 text-veridoc-700"
                  )}
                >
                  <span className="truncate block">{truncate(conv.title, 30)}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
