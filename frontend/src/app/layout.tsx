import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/components/AuthProvider";
import { ToastContainer } from "@/components/Toast";

export const metadata: Metadata = {
  title: "Veridoc — Answers you can verify, not just believe.",
  description:
    "Upload documents, ask questions in plain English, get answers grounded in and cited to the exact source passage.",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Prevent FOUC: set dark mode class before hydration */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var theme = localStorage.getItem('theme');
                  if (theme === 'dark' || (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                    document.documentElement.classList.add('dark');
                  }
                } catch(e) {}
              })();
            `,
          }}
        />
      </head>
      <body className="min-h-screen bg-gradient-to-br from-veridoc-50 via-white to-veridoc-100/20 dark:from-veridoc-950 dark:via-slate-900 dark:to-veridoc-900/20">
        <AuthProvider>{children}</AuthProvider>
        <ToastContainer />
      </body>
    </html>
  );
}
