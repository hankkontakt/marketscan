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

  // Decode JWT to check admin role.
  // Supabase always sets payload.role = "authenticated" (the PostgREST role).
  // Custom roles are stored in app_metadata — check there first, then fall back
  // to a direct profiles-table lookup via the API.
  try {
    const payload = JSON.parse(atob(session.access_token.split(".")[1]));
    // app_metadata.role is set via Supabase SQL:
    //   UPDATE auth.users SET raw_app_meta_data = raw_app_meta_data || '{"role":"admin"}' WHERE ...
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

  return <KontrollpanelView />;
}
