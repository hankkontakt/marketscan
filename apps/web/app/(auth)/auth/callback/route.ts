import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get("code");
  const type = searchParams.get("type");
  const rawNext = searchParams.get("next");
  const defaultNext = type === "recovery" ? "/installningar?tab=losenord" : "/oversikt";
  // Säkra mot Open Redirect: måste börja med / och inte // eller /\
  const isSafePath = rawNext && rawNext.startsWith("/") && !rawNext.startsWith("//") && !rawNext.startsWith("/\\");
  const next = isSafePath ? rawNext : defaultNext;

  if (!code) {
    return NextResponse.redirect(new URL("/login?error=auth_callback", request.url));
  }

  const redirectUrl = new URL(next, request.url);
  const response = NextResponse.redirect(redirectUrl);

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll(): { name: string; value: string }[] {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet: { name: string; value: string; options?: Record<string, unknown> }[]) {
          cookiesToSet.forEach(({ name, value, options }) => {
            request.cookies.set(name, value);
            response.cookies.set(name, value, options as Parameters<typeof response.cookies.set>[2]);
          });
        },
      },
    },
  );

  // Exchange the auth code for a session
  const { error } = await supabase.auth.exchangeCodeForSession(code);

  if (error) {
    return NextResponse.redirect(new URL("/login?error=auth_callback", request.url));
  }

  return response;
}
