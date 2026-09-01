import type { Metadata } from "next";
import { DECISIONS_V3_ENABLED } from "@/lib/v3";
import { BevakninarView } from "./BevakninarView";
import { BevakninarViewV3 } from "./BevakninarViewV3";

export const metadata: Metadata = { title: "Bevakningar" };

export default function BevakninarPage() {
  return DECISIONS_V3_ENABLED ? <BevakninarViewV3 /> : <BevakninarView />;
}
