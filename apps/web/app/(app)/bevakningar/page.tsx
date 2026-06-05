import type { Metadata } from "next";
import { BevakninarView } from "./BevakninarView";

export const metadata: Metadata = { title: "Bevakningar" };

export default function BevakninarPage() {
  return <BevakninarView />;
}
