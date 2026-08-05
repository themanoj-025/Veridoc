import type { Metadata } from "next";
import { Inter, Source_Serif_4, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/components/AuthProvider";
import { QueryProvider } from "@/components/QueryProvider";
import { ToastContainer } from "@/components/Toast";

// ── F17: Font loading via next/font (replaces CSS @import) ──

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const sourceSerif4 = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-source-serif",
  display: "swap",
  weight: ["400", "600", "700"],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
  weight: ["400", "500"],
});

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
      <body className={`${inter.variable} ${sourceSerif4.variable} ${jetbrainsMono.variable} min-h-screen bg-gradient-to-br from-veridoc-50 via-white to-veridoc-100/20 dark:from-veridoc-950 dark:via-slate-900 dark:to-veridoc-900/20`}>
        <QueryProvider><AuthProvider>{children}</AuthProvider></QueryProvider>
        <ToastContainer />
      </body>
    </html>
  );
}
