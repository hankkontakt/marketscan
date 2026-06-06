import type { Metadata } from "next";
import { JamforView } from "./JamforView";

export const metadata: Metadata = { title: "Jämför aktier" };

export default function JamforPage() {
  return <JamforView />;
}
