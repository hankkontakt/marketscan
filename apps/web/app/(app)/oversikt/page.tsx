import { redirect } from "next/navigation";

/** /oversikt → Daglig Briefing är nu startsidan */
export default function OversiktPage() {
  redirect("/daglig-briefing");
}
