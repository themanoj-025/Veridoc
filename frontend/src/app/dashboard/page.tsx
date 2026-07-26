"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import { documents, conversations, auth as authApi } from "@/lib/api";
import { ChatPanel } from "@/components/ChatPanel";
import { DocumentList } from "@/components/DocumentList";
import { DocumentViewer } from "@/components/DocumentViewer";
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
    try {
      const res = await documents.list();
      setDocList(res.data.documents || []);
    } catch (err) {
      console.error("Failed to load documents:", err);
    }
  };

  const loadConversations = async () => {
    try {
      const res = await conversations.list();
      setConvList(res.data.conversations || []);
    } catch (err) {
      console.error("Failed to load conversations:", err);
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
    const fileInput = form.elements.nativeElement?.querySelector('input[type="file"]') as HTMLInputElement;
    const titleInput = form.elements.nativeElement?.querySelector('input[name="title"]') as HTMLInputElement;

    if (!fileInput?.files?.length) return;

    setUploading(true);
    try {
      await documents.upload(fileInput.files[0], titleInput.value || undefined);
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
        <div className="w-8 h-8 rounded-full bg-veridoc-500 animate-pulse" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="h-14 border-b bg-white/80 backdrop-blur-sm flex items-center justify-between px-4 shrink-0 z-10">
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
              mobileView === "docs" ? "bg-veridoc-100 text-veridoc-700" : "text-muted-foreground")}>
            Docs
          </button>
          <button onClick={() => setMobileView("chat")}
            className={cn("px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
              mobileView === "chat" ? "bg-veridoc-100 text-veridoc-700" : "text-muted-foreground")}>
            Chat
          </button>
          {selectedDocId && (
            <button onClick={() => setMobileView("viewer")}
              className={cn("px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                mobileView === "viewer" ? "bg-veridoc-100 text-veridoc-700" : "text-muted-foreground")}>
              View
            </button>
          )}
        </div>

        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground hidden sm:block">
            {user?.email}
          </span>
          <button
            onClick={handleLogout}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Document sidebar - hidden on mobile when not active */}
        <div className={cn(
          "w-72 border-r bg-white flex flex-col shrink-0",
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
          />
        </div>

        {/* Document viewer */}
        <div className={cn(
          "flex-1 border-r bg-white/50 overflow-hidden",
          "md:block",
          mobileView !== "viewer" && "hidden md:hidden"
        )}>
          <DocumentViewer documentId={selectedDocId} />
        </div>

        {/* Chat panel */}
        <div className={cn(
          "w-[420px] border-l bg-white flex flex-col shrink-0",
          "md:flex",
          mobileView !== "chat" && "hidden"
        )}>
          <ChatPanel
            conversationId={conversationId}
            onNewConversation={handleNewConversation}
          />
        </div>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
             onClick={() => setShowUploadModal(false)}>
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold mb-4">Upload Document</h3>
            <form onSubmit={handleUpload} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Title <span className="text-muted-foreground">(optional)</span>
                </label>
                <input
                  name="title"
                  type="text"
                  className="w-full px-4 py-2 rounded-lg border border-input bg-white focus:outline-none focus:ring-2 focus:ring-veridoc-500/20 focus:border-veridoc-500"
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
                  className="w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-veridoc-50 file:text-veridoc-700 hover:file:bg-veridoc-100"
                />
              </div>
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
