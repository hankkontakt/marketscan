import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get("type");

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return request.cookies.getAll(); },
        setAll() {},
      },
    },
  );

  // Exchange the auth code for a session
  const { data, error } = await supabase.auth.exchangeCodeForSession(
    request.url,
  );

  if (error || !data.session) {
    return NextResponse.redirect(new URL("/login?error=auth_callback", request.url));
  }

  // If recovery flow, redirect to settings with password update
  if (type === "recovery") {
    return NextResponse.redirect(new URL("/installningar?tab=password", request.url));
  }

  return NextResponse.redirect(new URL("/oversikt", request.url));
}
