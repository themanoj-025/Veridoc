"use client";

import { useEffect, useState } from "react";
import { useDocumentContent } from "@/lib/queries";
import { t, tpl } from "@/lib/i18n";
import { OCRBadge } from "@/components/OCRBadge";

interface DocumentViewerProps {
  documentId: string | null;
}

export function DocumentViewer({ documentId }: DocumentViewerProps) {
  const {
    data: content,
    isLoading,
    error,
  } = useDocumentContent(documentId);
  // Track pending citation highlights that arrive before content loads
  const [pendingChunkId, setPendingChunkId] = useState<string | null>(null);

  // Register citation-highlight listener once on mount (F19)
  // We use a state setter so the event is captured even if content hasn't loaded yet
  useEffect(() => {
    const handler = (e: CustomEvent) => {
      setPendingChunkId(e.detail?.chunkId || null);
    };
    window.addEventListener("citation-highlight" as EventListener, handler);
    return () =>
      window.removeEventListener("citation-highlight" as EventListener, handler);
  }, []);

  // Scroll to chunk once both pendingChunkId AND content are available
  useEffect(() => {
    if (!pendingChunkId || !content?.chunks) return;
    const chunk = content.chunks.find(
      (c) => c.id === pendingChunkId || String(c.index) === pendingChunkId
    );
    if (!chunk) return;
    const el = document.getElementById(`chunk-${chunk.index}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add("ring-2", "ring-veridoc-500", "bg-veridoc-50/50");
      setTimeout(() => {
        el.classList.remove("ring-2", "ring-veridoc-500", "bg-veridoc-50/50");
      }, 3000);
    }
    setPendingChunkId(null);
  }, [pendingChunkId, content]);

  if (!documentId) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center p-8">
          <div className="w-16 h-16 rounded-2xl bg-veridoc-100 mx-auto mb-4 flex items-center justify-center">
            <svg className="w-8 h-8 text-veridoc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">{t("document.noSelection")}</h3>
          <p className="text-sm text-muted-foreground">
            {t("document.noSelectionHint")}
          </p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-veridoc-200 border-t-veridoc-500 animate-spin" />
          <p className="text-sm text-muted-foreground">{t("document.loading")}</p>
        </div>
      </div>
    );
  }

  if (error || !content) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-sm text-muted-foreground">
          {error ? `Error: ${error}` : t("document.notFound")}
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Document header */}
      <div className="p-4 border-b bg-card shrink-0">
        <h2 className="font-semibold text-foreground">{content.title}</h2>
        <p className="text-xs text-muted-foreground mt-1">
          {content.filename} · {content.status}
          {content.page_count != null && ` · ${tpl("document.pages", { count: content.page_count })}`}
          {content.chunk_count != null && ` · ${tpl("document.chunks", { count: content.chunk_count })}`}
        </p>
      </div>

      {/* Scrollable chunks */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {content.chunks.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-sm text-muted-foreground">
              {content.status === "indexed"
                ? t("document.noChunks")
                : t("document.processing")}
            </p>
          </div>
        ) : (
          content.chunks.map((chunk) => (
            <div
              key={chunk.index}
              id={`chunk-${chunk.index}`}
              className="p-4 rounded-xl border border-border bg-card transition-all duration-500 hover:border-veridoc-200"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-muted-foreground">
                  {tpl("document.chunkLabel", { index: chunk.index + 1 })}
                  {chunk.page_number != null && ` · ${tpl("citation.page", { page: chunk.page_number })}`}
                </span>
                <OCRBadge ocrUsed={chunk.ocr_used} size="xs" />
              </div>
              <p className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">
                {chunk.content}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
