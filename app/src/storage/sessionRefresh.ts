import type { AuthSession } from "@/api/types";

/** Renova se expires_at ausente ou expira dentro do buffer (default 1h). */
export function sessionNeedsRefresh(
  session: AuthSession,
  bufferMs = 3_600_000
): boolean {
  const refreshTok = session.refresh_token?.trim();
  if (!refreshTok) return false;
  const expiresAt = session.expires_at;
  if (typeof expiresAt !== "number" || expiresAt <= 0) return true;
  return expiresAt * 1000 < Date.now() + bufferMs;
}
