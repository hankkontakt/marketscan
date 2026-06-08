import withSerwistInit from "@serwist/next";
import type { NextConfig } from "next";

const withSerwist = withSerwistInit({
  swSrc: "app/sw.ts",
  swDest: "public/sw.js",
  disable: process.env.NODE_ENV === "development",
});

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "*.supabase.co" },
    ],
  },
  devIndicators: {
    buildActivity: false,
    buildActivityPosition: "bottom-right",
    appIsrStatus: false,
  },
  // Proxy /api/* → marketscan-api.vercel.app so browser sees one origin (no CORS needed)
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "https://marketscan-api.vercel.app/api/:path*",
      },
    ];
  },
};

export default withSerwist(nextConfig);
