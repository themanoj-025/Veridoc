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
  "auth.login.emailLabel": "Email",
  "auth.login.passwordLabel": "Password",
  "auth.login.submit": "Sign In",
  "auth.login.noAccount": "Don't have an account?",
  "auth.login.createOne": "Create one",
  "auth.register.title": "Get started with Veridoc",
  "auth.register.nameLabel": "Full Name",
  "auth.register.emailLabel": "Email",
  "auth.register.passwordLabel": "Password",
  "auth.register.submit": "Create Account",
  "auth.register.hasAccount": "Already have an account?",
  "auth.register.signIn": "Sign in",

  // ── Dashboard ──
  "dashboard.title": "Veridoc",
  "dashboard.loading": "Loading Veridoc...",
  "dashboard.searchPlaceholder": "Search documents & conversations...",
  "dashboard.signOut": "Sign out",
  "dashboard.newChat": "+ New Chat",

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
  "chat.fallbackModel": "⚠️ Answered via fallback model",
  "chat.faithfulLabel": "% faithful",

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
