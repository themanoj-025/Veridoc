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
import { searchApi } from "@/lib/api";
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
  const [fullTextResults, setFullTextResults] = useState<any[] | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deletingAccount, setDeletingAccount] = useState(false);
  const [showMobileSearch, setShowMobileSearch] = useState(false);

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

  const handleFullTextSearch = async (query: string) => {
    try {
      const res = await searchApi.fulltext(query);
      setFullTextResults(res.data.results || []);
      if (res.data.total > 0) {
        toast.success(`Found ${res.data.total} results for "${query}"`);
      } else {
        toast.info("No results found", `No matches for "${query}"`);
      }
    } catch (err) {
      console.error("Full-text search failed:", err);
      toast.error("Search failed");
    }
  };

  const handleDeleteAccount = async () => {
    setDeletingAccount(true);
    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API_BASE}/api/v1/user/delete-account`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        toast.success("Account deleted", "All your data has been permanently removed");
        logout();
        router.replace("/login");
      } else {
        const data = await res.json();
        toast.error("Delete failed", data.detail || "Something went wrong");
      }
    } catch (err: any) {
      toast.error("Delete failed", err.message || "Network error");
    } finally {
      setDeletingAccount(false);
      setShowDeleteConfirm(false);
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

        {/* Desktop search bar */}
        <div className="hidden sm:flex items-center flex-1 max-w-md mx-4">
          <SearchBar
            documents={docList}
            conversations={convList}
            onSelectDocument={(id) => { setSelectedDocId(id); setMobileView("viewer"); }}
            onSelectConversation={(id) => { setConversationId(id); setMobileView("chat"); }}
            onFullTextSearch={handleFullTextSearch}
          />
        </div>

        {/* Mobile search trigger */}
        <button
          onClick={() => setShowMobileSearch(true)}
          className="sm:hidden text-muted-foreground hover:text-foreground transition-colors p-2 rounded-lg hover:bg-surface-hover"
          title="Search"
          aria-label="Search documents and conversations"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </button>

        <div className="flex items-center gap-1">
          {/* GDPR: Export data */}
          <button
            onClick={async () => {
              try {
                const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const token = localStorage.getItem("access_token");
                const res = await fetch(`${API_BASE}/api/v1/user/export`, {
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

          {/* GDPR: Delete account */}
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="text-muted-foreground hover:text-red-600 transition-colors p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20"
            title="Delete account and all data (GDPR)"
            aria-label="Delete account"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>

          <ThemeToggle />
          <span className="text-sm text-muted-foreground hidden md:block mx-2">
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
          mobileView !== "docs" && "hidden",
          mobileView === "docs" && "animate-fade-in"
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
          mobileView === "viewer" ? "animate-fade-in" : "",
          "md:block",
          mobileView !== "viewer" && "hidden"
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
          mobileView !== "chat" && "hidden",
          mobileView === "chat" && "animate-fade-in"
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

      {/* Mobile search overlay */}
      {showMobileSearch && (
        <div className="fixed inset-0 z-50 sm:hidden animate-fade-in">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowMobileSearch(false)} />
          <div className="absolute top-0 left-0 right-0 bg-card border-b border-border rounded-b-2xl shadow-xl p-4 animate-slide-up">
            <div className="flex items-center gap-3 mb-3">
              <svg className="w-5 h-5 text-muted-foreground shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                id="mobile-search-input"
                autoFocus
                placeholder="Search documents, conversations..."
                className="flex-1 bg-transparent text-foreground placeholder-muted-foreground outline-none text-sm"
                onKeyDown={(e) => {
                  if (e.key === "Escape") setShowMobileSearch(false);
                }}
              />
              <button
                onClick={() => setShowMobileSearch(false)}
                className="text-sm text-veridoc-500 font-medium"
              >
                Cancel
              </button>
            </div>
            <div className="max-h-60 overflow-y-auto">
              {docList.length === 0 && convList.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-6">
                  No documents or conversations yet
                </p>
              ) : (
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground font-medium px-2 py-1">Documents</p>
                  {docList.slice(0, 5).map((doc) => (
                    <button
                      key={doc.id}
                      onClick={() => { setSelectedDocId(doc.id); setMobileView("viewer"); setShowMobileSearch(false); }}
                      className="w-full text-left px-3 py-2 rounded-lg hover:bg-secondary transition-colors text-sm"
                    >
                      <span className="font-medium text-foreground">{doc.title}</span>
                      <span className="text-xs text-muted-foreground ml-2">{doc.file_type.toUpperCase()}</span>
                    </button>
                  ))}
                  {convList.length > 0 && (
                    <>
                      <p className="text-xs text-muted-foreground font-medium px-2 py-1 mt-2">Conversations</p>
                      {convList.slice(0, 5).map((conv) => (
                        <button
                          key={conv.id}
                          onClick={() => { setConversationId(conv.id); setMobileView("chat"); setShowMobileSearch(false); }}
                          className="w-full text-left px-3 py-2 rounded-lg hover:bg-secondary transition-colors text-sm"
                        >
                          <span className="text-foreground">{conv.title || "Untitled"}</span>
                        </button>
                      ))}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Delete Account Confirmation Dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
             onClick={() => setShowDeleteConfirm(false)}>
          <div className="bg-card rounded-2xl shadow-xl border border-border p-6 w-full max-w-md animate-scale-in" onClick={(e) => e.stopPropagation()}>
            <div className="w-12 h-12 rounded-2xl bg-red-100 dark:bg-red-900/30 mx-auto mb-4 flex items-center justify-center">
              <svg className="w-6 h-6 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-center mb-2">Delete Account</h3>
            <p className="text-sm text-muted-foreground text-center mb-6">
              This will permanently delete your account and all associated data,
              including documents, conversations, and usage history.
              <strong className="text-red-600 dark:text-red-400 block mt-2">This action cannot be undone.</strong>
            </p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={deletingAccount}
                className="px-4 py-2 rounded-lg border text-sm font-medium hover:bg-secondary transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAccount}
                disabled={deletingAccount}
                className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                {deletingAccount ? "Deleting..." : "Yes, delete my account"}
              </button>
            </div>
          </div>
        </div>
      )}

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
