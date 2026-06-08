import { defaultCache } from "@serwist/next/worker";
import type { PrecacheEntry, SerwistGlobalConfig } from "serwist";
import { Serwist, NetworkOnly } from "serwist";

declare global {
  interface WorkerGlobalScope extends SerwistGlobalConfig {
    __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
  }
}

declare const self: WorkerGlobalScope;

// API calls must go directly to the network — never cache, never timeout.
// Using NetworkFirst with a short timeout caused "Failed to fetch" when the
// serverless API was cold-starting (> 5 s). NetworkOnly bypasses this entirely.
const apiRoute = {
  matcher: ({ url }: { url: URL }) => url.pathname.startsWith("/api/"),
  handler: new NetworkOnly(),
};

const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: true,
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: [...defaultCache, apiRoute],
});

serwist.addEventListeners();
