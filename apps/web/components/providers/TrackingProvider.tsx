"use client";

import Script from "next/script";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { trackPageView } from "@/lib/tracking";

const UMAMI_URL = process.env.NEXT_PUBLIC_UMAMI_URL || "";
const WEBSITE_ID = process.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID || "";

export function TrackingProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  // Track client-side navigations
  useEffect(() => {
    trackPageView(pathname);
  }, [pathname]);

  // Om ingen URL/ID konfigurerats, rendera bara children (ingen krasch)
  if (!UMAMI_URL || !WEBSITE_ID) {
    return <>{children}</>;
  }

  return (
    <>
      <Script
        src={`${UMAMI_URL}/umami.js`}
        data-website-id={WEBSITE_ID}
        data-domains={process.env.NEXT_PUBLIC_APP_DOMAIN}
        strategy="afterInteractive"
        defer
      />
      {children}
    </>
  );
}
