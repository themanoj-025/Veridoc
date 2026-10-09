/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/:path*`,
      },
    ];
  },
};

// ── F15: Bundle analysis ─────────────────────────────────────
// Run: ANALYZE=true npm run build
// Opens interactive treemap in the browser showing each chunk's composition.
const withBundleAnalyzer =
  process.env.ANALYZE === "true"
    ? require("@next/bundle-analyzer")({
        enabled: true,
        openAnalyzer: true,
      })
    : (config) => config;

module.exports = withBundleAnalyzer(nextConfig);
