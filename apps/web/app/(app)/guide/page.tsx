import type { Metadata } from "next";
import { GuideView } from "./GuideView";

export const metadata: Metadata = { title: "Guide" };

export default function GuidePage() {
  return <GuideView />;
}
