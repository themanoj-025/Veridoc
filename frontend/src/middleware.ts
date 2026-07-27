import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Content-Security-Policy for Veridoc.
 *
 * In production (NODE_ENV=production) the policy is locked down to
 * same-origin only. In development more inline sources are allowed to
 * support Next.js hot-reload and React DevTools.
 */
export function middleware(request: NextRequest) {
  const isDev = process.env.NODE_ENV !== "production";

  const directives = [
    "default-src 'self'",
    // Scripts – Next.js hydration scripts use inline in dev
    // Next.js injects inline bootstrap scripts (e.g. __NEXT_DATA__)
    // in both dev and production — 'unsafe-inline' is required.
    isDev
      ? "script-src 'self' 'unsafe-inline' 'unsafe-eval'"
      : "script-src 'self' 'unsafe-inline'",
    // Styles – Tailwind generates inline styles
    "style-src 'self' 'unsafe-inline'",
    // Images – allow data: URIs for icons and blob: for document preview
    "img-src 'self' data: blob:",
    // Fonts
    "font-src 'self' data:",
    // API / SSE connections – same-origin covers Next.js rewrites
    "connect-src 'self' ws: wss:",
    // Forms
    "form-action 'self'",
    // Prevent framing
    "frame-ancestors 'none'",
    // Base URI
    "base-uri 'self'",
  ].join("; ");

  const requestHeaders = new Headers(request.headers);

  const response = NextResponse.next({
    request: { headers: requestHeaders },
  });

  response.headers.set("Content-Security-Policy", directives);
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");

  return response;
}

export const config = {
  matcher: [
    // Apply to all routes except static assets and Next.js internals
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
