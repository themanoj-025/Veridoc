"use client";

import { useEffect, useState } from "react";
import { documents } from "@/lib/api";

interface DocumentViewerProps {
  documentId: string | null;
}

export function DocumentViewer({ documentId }: DocumentViewerProps) {
  const [doc, setDoc] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [highlightId, setHighlightId] = useState<string | null>(null);

  useEffect(() => {
    if (!documentId) {
      setDoc(null);
      return;
    }
    setLoading(true);
    documents.get(documentId).then((res) => {
      setDoc(res.data);
    }).catch(console.error).finally(() => setLoading(false));
  }, [documentId]);

  // Listen for citation highlight events
  useEffect(() => {
    const handler = (e: CustomEvent) => {
      setHighlightId(e.detail?.chunkId || null);
      setTimeout(() => setHighlightId(null), 3000);
    };
    window.addEventListener("citation-highlight" as any, handler as any);
    return () => window.removeEventListener("citation-highlight" as any, handler as any);
  }, []);

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
          <h3 className="text-lg font-semibold text-foreground mb-2">No document selected</h3>
          <p className="text-sm text-muted-foreground">
            Select a document from the sidebar to view its contents
          </p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-veridoc-200 border-t-veridoc-500 animate-spin" />
          <p className="text-sm text-muted-foreground">Loading document...</p>
        </div>
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-sm text-muted-foreground">Document not found</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Document header */}
      <div className="p-4 border-b bg-white">
        <h2 className="font-semibold text-foreground">{doc.title}</h2>
        <p className="text-xs text-muted-foreground mt-1">
          {doc.filename} · {doc.status}
          {doc.page_count && ` · ${doc.page_count} pages`}
          {doc.chunk_count && ` · ${doc.chunk_count} chunks`}
        </p>
      </div>

      {/* Document content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-none document-page">
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-veridoc-50 border border-veridoc-100">
              <p className="text-sm text-veridoc-700 font-medium mb-2">Document Info</p>
              <dl className="text-sm space-y-1 text-muted-foreground">
                <dt className="inline font-medium">Title:</dt>
                <dd className="inline ml-1">{doc.title}</dd>
                <br />
                <dt className="inline font-medium">File:</dt>
                <dd className="inline ml-1">{doc.filename}</dd>
                <br />
                <dt className="inline font-medium">Type:</dt>
                <dd className="inline ml-1">{doc.file_type.toUpperCase()}</dd>
                <br />
                <dt className="inline font-medium">Status:</dt>
                <dd className="inline ml-1">{doc.status}</dd>
                <br />
                <dt className="inline font-medium">Created:</dt>
                <dd className="inline ml-1">{new Date(doc.created_at).toLocaleDateString()}</dd>
              </dl>
            </div>

            {doc.status === "indexed" && (
              <div className="p-4 rounded-xl bg-green-50 border border-green-200 text-green-700 text-sm">
                Document has been indexed and is ready for questions.
              </div>
            )}

            {doc.status === "failed" && (
              <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
                Failed to process: {doc.error_message}
              </div>
            )}

            {doc.status === "pending" || doc.status === "parsing" || doc.status === "chunking" || doc.status === "embedding" || doc.status === "indexing" ? (
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-700 text-sm">
                Processing document...
              </div>
            ) : null}

            {/* Citation highlight placeholder */}
            {highlightId && (
              <div id={`citation-${highlightId}`} className="p-4 rounded-xl bg-accent/10 border border-accent/30 animate-fade-in">
                <p className="text-sm text-accent-dark">
                  <span className="font-medium">Highlighted passage</span>
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
