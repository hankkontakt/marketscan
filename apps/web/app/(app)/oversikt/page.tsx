import type { Metadata } from "next";
import { OversiktView } from "./OversiktView";

export const metadata: Metadata = { title: "Översikt" };

export default function OversiktPage() {
  return <OversiktView />;
}
