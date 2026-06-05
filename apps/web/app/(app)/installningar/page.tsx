import type { Metadata } from "next";
import { InstallningarView } from "./InstallningarView";

export const metadata: Metadata = { title: "Inställningar" };

export default function InstallningarPage() {
  return <InstallningarView />;
}
