import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { Metadata } from "next";
import { KontrollpanelView } from "./KontrollpanelView";

export const metadata: Metadata = { title: "Kontrollpanel" };

export default async function KontrollpanelPage() {
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

  const { data: { session } } = await supabase.auth.getSession();

  if (!session?.access_token) {
    redirect("/login?redirect=/kontrollpanel");
  }

  // Decode JWT to check role (mirrors the API logic in security.py)
  try {
    const payload = JSON.parse(atob(session.access_token.split(".")[1]));
    const role: string = payload.role ?? "user";
    if (role !== "admin") {
      redirect("/oversikt");
    }
  } catch {
    redirect("/oversikt");
  }

  return <KontrollpanelView />;
}
