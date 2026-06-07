import { defaultCache } from "@serwist/next/worker";
import type { PrecacheEntry, SerwistGlobalConfig } from "serwist";
import { Serwist, NetworkFirst } from "serwist";

declare global {
  interface WorkerGlobalScope extends SerwistGlobalConfig {
    __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
  }
}

declare const self: WorkerGlobalScope;

// Add NetworkFirst strategy for API calls with 5s timeout
const apiCache = {
  matcher: ({ url }: { url: URL }) => url.pathname.startsWith("/api/"),
  handler: new NetworkFirst({
    networkTimeoutSeconds: 5,
    cacheName: "api-cache",
    plugins: [
      {
        cacheWillUpdate: async () => null, // never cache API responses
      },
    ],
  }),
};

const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: true,
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: [...defaultCache, apiCache],
});

serwist.addEventListeners();
