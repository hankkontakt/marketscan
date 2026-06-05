import type { Metadata } from "next";
import { KontrollpanelView } from "./KontrollpanelView";

export const metadata: Metadata = { title: "Kontrollpanel" };

export default function KontrollpanelPage() {
  return <KontrollpanelView />;
}
