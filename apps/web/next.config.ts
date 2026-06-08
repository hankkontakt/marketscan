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
  // NOTE: no /api/* rewrite proxy. The browser calls the API host directly
  // (see lib/api.ts → API_BASE). Proxying same-origin would route through THIS
  // deployment's Vercel Deployment Protection and break authenticated POSTs.
};

export default withSerwist(nextConfig);
