import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { Metadata } from "next";
import { AiPrestandaView } from "./AiPrestandaView";

export const metadata: Metadata = { title: "AI-prestanda" };

export default async function AiPrestandaPage() {
  const cookieStore = await cookies();
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
      },
    },
  );

  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    redirect("/login?redirect=/ai-prestanda");
  }

  // Verify admin role (same pattern as kontrollpanel/page.tsx)
  try {
    const payload = JSON.parse(atob(session.access_token.split(".")[1]));
    const role: string =
      (payload.app_metadata?.role as string | undefined) ??
      (payload.user_metadata?.role as string | undefined) ??
      "user";
    if (role !== "admin") {
      redirect("/oversikt");
    }
  } catch {
    redirect("/oversikt");
  }

  return <AiPrestandaView />;
}
