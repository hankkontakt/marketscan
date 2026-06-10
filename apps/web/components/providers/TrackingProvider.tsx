"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { trackPageView } from "@/lib/tracking";

/**
 * TrackingProvider — mounts once and tracks page views on navigation.
 * No external dependencies — works out of the box using Supabase-backed API.
 */
export function TrackingProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  useEffect(() => {
    trackPageView(pathname);
  }, [pathname]);

  return <>{children}</>;
}
