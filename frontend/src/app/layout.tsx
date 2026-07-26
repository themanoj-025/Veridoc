import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/components/AuthProvider";

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
    <html lang="en" className="light">
      <body className="min-h-screen bg-gradient-to-br from-veridoc-50 via-white to-veridoc-100/20">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
