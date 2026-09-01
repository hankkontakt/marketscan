/**
 * Utility to extract user role and admin status from Supabase JWT token.
 */
export function getRoleFromJwt(token: string | null | undefined): string {
  if (!token) return "";
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return (
      (payload.app_metadata?.role as string | undefined) ??
      (payload.user_metadata?.role as string | undefined) ??
      ""
    );
  } catch {
    return "";
  }
}

export function isUserAdmin(token: string | null | undefined): boolean {
  return getRoleFromJwt(token) === "admin";
}
