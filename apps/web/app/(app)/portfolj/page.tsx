import type { Metadata } from "next";
import { PortfoljView } from "./PortfoljView";

export const metadata: Metadata = { title: "Min portfölj" };

export default function PortfoljPage() {
  return <PortfoljView />;
}
