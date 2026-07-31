/**
 * G9: i18n scaffold — translation key structure with English as shipped locale.
 *
 * Usage in components:
 *   import { t } from "@/lib/i18n";
 *   <h1>{t("dashboard.title")}</h1>
 *
 * To add a new language:
 *   1. Create a new file: frontend/public/locales/{lang}/common.json
 *   2. Import it here and add to the messages map.
 *
 * All user-facing strings should be extracted to this key structure.
 * Currently only English is shipped. Adding a new language is a config change,
 * not a code rewrite.
 */

// ── Translation keys (English) ─────────────────────────────

const en: Record<string, string> = {
  // ── Auth pages ──
  "auth.login.title": "Sign in to Veridoc",
  "auth.login.tagline": "Answers you can verify, not just believe.",
  "auth.login.emailLabel": "Email",
  "auth.login.passwordLabel": "Password",
  "auth.login.emailPlaceholder": "you@example.com",
  "auth.login.passwordPlaceholder": "••••••••",
  "auth.login.submit": "Sign in",
  "auth.login.submitting": "Signing in...",
  "auth.login.error": "Login failed. Please try again.",
  "auth.login.noAccount": "Don't have an account?",
  "auth.login.createOne": "Create one",
  "auth.register.title": "Get started with Veridoc",
  "auth.register.tagline": "Create your account",
  "auth.register.heading": "Get started",
  "auth.register.nameLabel": "Full name",
  "auth.register.nameOptional": "(optional)",
  "auth.register.namePlaceholder": "Jane Doe",
  "auth.register.emailLabel": "Email",
  "auth.register.passwordLabel": "Password",
  "auth.register.passwordPlaceholder": "Min. 8 characters",
  "auth.register.submit": "Create account",
  "auth.register.submitting": "Creating account...",
  "auth.register.error": "Registration failed. Please try again.",
  "auth.register.hasAccount": "Already have an account?",
  "auth.register.signIn": "Sign in",

  // ── Dashboard ──
  "dashboard.title": "Veridoc",
  "dashboard.loading": "Loading Veridoc...",
  "dashboard.searchPlaceholder": "Search documents & conversations...",
  "dashboard.searchMobilePlaceholder": "Search documents, conversations...",
  "dashboard.signOut": "Sign out",
  "dashboard.newChat": "+ New Chat",
  "dashboard.docs": "Docs",
  "dashboard.chat": "Chat",
  "dashboard.view": "View",
  "dashboard.navigation": "Navigation",
  "dashboard.cancel": "Cancel",
  "dashboard.noDocsOrConvs": "No documents or conversations yet",
  "dashboard.documents": "Documents",
  "dashboard.conversations": "Conversations",
  "dashboard.untitled": "Untitled",
  "dashboard.adminAnalytics": "Admin analytics",
  "dashboard.openSidebar": "Open sidebar",
  "dashboard.uploadTitle": "Upload Document",
  "dashboard.uploadTitleOptional": "Title (optional)",
  "dashboard.uploadFileLabel": "File (PDF, DOCX, TXT)",
  "dashboard.uploadPlaceholder": "My Document",
  "dashboard.uploading": "Uploading...",
  "dashboard.upload": "Upload",
  "dashboard.deleteTitle": "Delete Account",
  "dashboard.deleteMessage": "This will permanently delete your account and all associated data, including documents, conversations, and usage history.",
  "dashboard.deleteWarning": "This action cannot be undone.",
  "dashboard.deleteConfirm": "Yes, delete my account",
  "dashboard.deleting": "Deleting...",
  "dashboard.accountDeleted": "Account deleted",
  "dashboard.accountDeletedDetail": "All your data has been permanently removed",
  "dashboard.deleteFailed": "Delete failed",
  "dashboard.searchFailed": "Search failed",
  "dashboard.searchResults": "Found {count} results for \"{query}\"",
  "dashboard.noResults": "No results found",

  // ── Documents ──
  "documents.upload": "Upload Document",
  "documents.noDocuments": "No documents yet",
  "documents.uploadHint": "Upload a PDF, DOCX, or TXT file to get started",
  "documents.statusIndexed": "Indexed",
  "documents.statusFailed": "Failed",
  "documents.statusProcessing": "Processing...",

  // ── Chat ──
  "chat.title": "Chat",
  "chat.inputPlaceholder": "Ask a question...",
  "chat.startPlaceholder": "Start a new conversation...",
  "chat.emptyState": "Ask a question about your documents",
  "chat.send": "Send",
  "chat.reconnecting": "Reconnecting...",
  "chat.fallbackModel": "⚠️ Answered via fallback model",
  "chat.faithfulLabel": "{percent}% faithful",

  // ── Citations ──
  "citation.sources": "Sources:",
  "citation.page": "p.{page}",
  "citation.src": "src {index}",

  // ── Feedback ──
  "feedback.wasHelpful": "Was this helpful?",
  "feedback.thanks": "Thanks for your feedback!",
  "feedback.recorded": "Feedback recorded",
  "feedback.improveHint": "This will help improve future responses.",

  // ── Confidence badge (G1) ──
  "confidence.high": "High confidence",
  "confidence.medium": "Medium confidence",
  "confidence.low": "Low confidence",

  // ── GDPR ──
  "gdpr.exportData": "Export my data",
  "gdpr.deleteAccount": "Delete account and all data",
  "gdpr.exportSuccess": "Data exported",
  "gdpr.downloadStarted": "Download started",
  "gdpr.exportFailed": "Export failed",
  "gdpr.deleteConfirmTitle": "Delete Account",
  "gdpr.deleteConfirmMessage": "This will permanently delete your account and all associated data.",
  "gdpr.deleteConfirmWarning": "This action cannot be undone.",
  "gdpr.cancel": "Cancel",
  "gdpr.deleteConfirm": "Yes, delete my account",
  "gdpr.deleting": "Deleting...",
  "gdpr.deleteSuccess": "Account deleted",
  "gdpr.deleteSuccessDetail": "All your data has been permanently removed",
  "gdpr.deleteFailed": "Delete failed",

  // ── Document list (G9) ──
  "documents.listTitle": "Documents",
  "documents.conversations": "Conversations",
  "documents.new": "+ New",
  "documents.noConversations": "No conversations yet",

  // ── Command palette (G9) ──
  "command.newChat": "New Conversation",
  "command.newChatDesc": "Start a new chat conversation",
  "command.toggleTheme": "Toggle Dark Mode",
  "command.toggleThemeDesc": "Switch between light and dark theme",
  "command.uploadDesc": "Upload a PDF, DOCX, or TXT file",
  "command.searchDocs": "Search Documents",
  "command.searchDocsDesc": "Search across all your documents",
  "command.signOutDesc": "Log out of your account",
  "command.searchPlaceholder": "Search commands...",
  "command.footerPress": "Press",
  "command.footerNavigate": "to navigate,",
  "command.footerSelect": "to select",

  // ── Search (G9) ──
  "search.fullText": "Search inside documents for \u201C{query}\u201D",

  // ── Document viewer (F19/G9) ──
  "document.noSelection": "No document selected",
  "document.noSelectionHint": "Select a document from the sidebar to view its contents",
  "document.loading": "Loading document...",
  "document.notFound": "Document not found",
  "document.noChunks": "No chunks available for this document.",
  "document.processing": "Document is still being processed. Chunks will appear once indexing completes.",
  "document.chunkLabel": "Chunk {index}",
  "document.pages": "{count} pages",
  "document.chunks": "{count} chunks",

  // ── Feedback buttons (G9) ──
  "feedback.helpful": "Helpful",
  "feedback.notHelpful": "Not helpful",
  "feedback.thumbsUp": "Thumbs up",
  "feedback.thumbsDown": "Thumbs down",

  // ── Common UI ──
  "common.loading": "Loading...",
  "common.error": "Error",
  "common.retry": "Retry",
  "common.cancel": "Cancel",
  "common.close": "Close",
  "common.search": "Search",
  "common.noResults": "No results found",
};

export type TranslationKey = keyof typeof en;

/**
 * Get a translated string by key.
 * Falls back to the key itself if no translation is found.
 */
export function t(key: TranslationKey): string {
  return en[key] ?? key;
}

/**
 * Get a translated string with interpolation.
 * Usage: tpl("chat.page", { page: 5 }) => "p.5"
 */
export function tpl(key: TranslationKey, params: Record<string, string | number>): string {
  let value = en[key] ?? key;
  for (const [k, v] of Object.entries(params)) {
    value = value.replace(`{${k}}`, String(v));
  }
  return value;
}
