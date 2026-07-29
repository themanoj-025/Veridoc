"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import { documents, conversations, auth as authApi } from "@/lib/api";
import { ChatPanel } from "@/components/ChatPanel";
import { DocumentList } from "@/components/DocumentList";
import { DocumentViewer } from "@/components/DocumentViewer";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { ThemeToggle } from "@/components/ThemeToggle";
import { CommandPalette } from "@/components/CommandPalette";
import { SearchBar } from "@/components/SearchBar";
import { DocumentListSkeleton, DocumentViewerSkeleton, ChatMessageSkeleton } from "@/components/Skeleton";
import { toast } from "@/lib/toast-store";
import { cn } from "@/lib/utils";

export default function Dashboard() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, logout } = useAuthStore();

  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [docList, setDocList] = useState<any[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [convList, setConvList] = useState<any[]>([]);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [loadingConvs, setLoadingConvs] = useState(true);
  const [mobileView, setMobileView] = useState<"docs" | "chat" | "viewer">("docs");

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadDocuments();
      loadConversations();
    }
  }, [isAuthenticated]);

  const loadDocuments = async () => {
    setLoadingDocs(true);
    try {
      const res = await documents.list();
      setDocList(res.data.items || []);
    } catch (err) {
      console.error("Failed to load documents:", err);
    } finally {
      setLoadingDocs(false);
    }
  };

  const loadConversations = async () => {
    setLoadingConvs(true);
    try {
      const res = await conversations.list();
      setConvList(res.data.items || []);
    } catch (err) {
      console.error("Failed to load conversations:", err);
    } finally {
      setLoadingConvs(false);
    }
  };

  const handleNewConversation = async () => {
    try {
      const docIds = selectedDocId ? [selectedDocId] : [];
      const res = await conversations.create({ document_ids: docIds });
      setConversationId(res.data.id);
      setConvList((prev) => [res.data, ...prev]);
      setMobileView("chat");
    } catch (err) {
      console.error("Failed to create conversation:", err);
    }
  };

  const handleUpload = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const formData = new FormData(form);
    const file = formData.get("file") as File | null;
    const title = formData.get("title") as string | null;

    if (!file) return;

    setUploading(true);
    try {
      await documents.upload(file, title || undefined);
      setShowUploadModal(false);
      loadDocuments();
    } catch (err) {
      console.error("Upload failed:", err);
    } finally {
      setUploading(false);
    }
  };

  const handleLogout = () => {
    logout();
    router.replace("/login");
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-veridoc-500 animate-pulse-slow" />
          <p className="text-sm text-muted-foreground font-medium">Loading Veridoc...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="h-screen flex flex-col bg-background">
      <CommandPalette />
      {/* Header */}
      <header className="h-14 border-b bg-card/80 backdrop-blur-sm flex items-center justify-between px-4 shrink-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-veridoc-500 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <span className="font-semibold text-foreground">Veridoc</span>
        </div>

        {/* Mobile tabs */}
        <div className="flex items-center gap-2 md:hidden">
          <button onClick={() => setMobileView("docs")}
            className={cn("px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
              mobileView === "docs" ? "bg-veridoc-100 text-veridoc-700 dark:bg-veridoc-900/50 dark:text-veridoc-300" : "text-muted-foreground")}>
            Docs
          </button>
          <button onClick={() => setMobileView("chat")}
            className={cn("px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
              mobileView === "chat" ? "bg-veridoc-100 text-veridoc-700 dark:bg-veridoc-900/50 dark:text-veridoc-300" : "text-muted-foreground")}>
            Chat
          </button>
          {selectedDocId && (
            <button onClick={() => setMobileView("viewer")}
              className={cn("px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                mobileView === "viewer" ? "bg-veridoc-100 text-veridoc-700 dark:bg-veridoc-900/50 dark:text-veridoc-300" : "text-muted-foreground")}>
              View
            </button>
          )}
        </div>

        <div className="hidden sm:flex items-center flex-1 max-w-md mx-4">
          <SearchBar
            documents={docList}
            conversations={convList}
            onSelectDocument={(id) => { setSelectedDocId(id); setMobileView("viewer"); }}
            onSelectConversation={(id) => { setConversationId(id); setMobileView("chat"); }}
          />
        </div>

        <div className="flex items-center gap-1">
          {/* GDPR: Export data */}
          <button
            onClick={async () => {
              try {
                const token = localStorage.getItem("access_token");
                const res = await fetch(`http://localhost:8000/api/v1/user/export`, {
                  headers: { Authorization: `Bearer ${token}` },
                });
                if (res.ok) {
                  const blob = await res.blob();
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `veridoc-export.json`;
                  a.click();
                  URL.revokeObjectURL(url);
                  toast.success("Data exported", "Download started");
                }
              } catch {
                toast.error("Export failed");
              }
            }}
            className="text-muted-foreground hover:text-foreground transition-colors p-2 rounded-lg hover:bg-surface-hover"
            title="Export my data (GDPR)"
            aria-label="Export data"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </button>
          <ThemeToggle />
          <span className="text-sm text-muted-foreground hidden sm:block mx-2">
            {user?.email}
          </span>
          <button
            onClick={handleLogout}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors px-2 py-1"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Document sidebar - hidden on mobile when not active */}
        <div className={cn(
          "w-72 border-r bg-card flex flex-col shrink-0",
          "md:flex",
          mobileView !== "docs" && "hidden"
        )}>
          <DocumentList
            documents={docList}
            selectedId={selectedDocId}
            onSelect={(id) => { setSelectedDocId(id); setMobileView("viewer"); }}
            onUpload={() => setShowUploadModal(true)}
            onNewChat={handleNewConversation}
            selectedConversationId={conversationId}
            conversations={convList}
            onSelectConversation={(id) => { setConversationId(id); setMobileView("chat"); }}
            loading={loadingDocs}
          />
        </div>

        {/* Document viewer */}
        <div className={cn(
          "flex-1 border-r bg-card/50 overflow-hidden",
          "md:block",
          mobileView !== "viewer" && "hidden md:hidden"
        )}>
          {loadingDocs && selectedDocId ? (
            <DocumentViewerSkeleton />
          ) : (
            <ErrorBoundary name="Document Viewer">
              <DocumentViewer documentId={selectedDocId} />
            </ErrorBoundary>
          )}
        </div>

        {/* Chat panel */}
        <div className={cn(
          "w-[420px] border-l bg-card flex flex-col shrink-0",
          "md:flex",
          mobileView !== "chat" && "hidden"
        )}>
          {loadingConvs && conversationId ? (
            <div className="p-4">
              <ChatMessageSkeleton />
            </div>
          ) : (
            <ErrorBoundary name="Chat Panel">
              <ChatPanel
                conversationId={conversationId}
                onNewConversation={handleNewConversation}
              />
            </ErrorBoundary>
          )}
        </div>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
             onClick={() => setShowUploadModal(false)}>
          <div className="bg-card rounded-2xl shadow-xl border border-border p-6 w-full max-w-md animate-scale-in" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold mb-4">Upload Document</h3>
            <form onSubmit={handleUpload} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Title <span className="text-muted-foreground">(optional)</span>
                </label>
                <input
                  name="title"
                  type="text"
                  className="w-full px-4 py-2 rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-veridoc-500/20 focus:border-veridoc-500 transition-all"
                  placeholder="My Document"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  File (PDF, DOCX, TXT)
                </label>
                <input
                  type="file"
                  accept=".pdf,.docx,.doc,.txt"
                  required
                  className="w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-veridoc-50 file:text-veridoc-700 dark:file:bg-veridoc-900/50 dark:file:text-veridoc-300 hover:file:bg-veridoc-100 dark:hover:file:bg-veridoc-800/50"
                />
              </div>
              {uploading && (
                <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-veridoc-500 rounded-full animate-pulse" style={{ width: "60%" }} />
                </div>
              )}
              <div className="flex gap-3 justify-end">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 rounded-lg border text-sm font-medium hover:bg-secondary transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading}
                  className="px-4 py-2 rounded-lg bg-veridoc-500 text-white text-sm font-medium hover:bg-veridoc-600 disabled:opacity-50 transition-colors"
                >
                  {uploading ? "Uploading..." : "Upload"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
