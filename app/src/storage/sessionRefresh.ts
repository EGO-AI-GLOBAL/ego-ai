import type { AuthSession } from "@/api/types";

function expiresAtMs(session: AuthSession): number | null {
  const expiresAt = session.expires_at as unknown;
  if (typeof expiresAt === "number" && Number.isFinite(expiresAt) && expiresAt > 0) {
    return expiresAt * 1000;
  }
  if (typeof expiresAt === "string" && /^\d+$/.test(expiresAt.trim())) {
    const n = parseInt(expiresAt.trim(), 10);
    return n > 0 ? n * 1000 : null;
  }
  return null;
}

/** Renova se expires_at ausente ou expira dentro do buffer (default 5 min). */
export function sessionNeedsRefresh(
  session: AuthSession,
  bufferMs = 300_000
): boolean {
  const refreshTok = session.refresh_token?.trim();
  if (!refreshTok) return false;
  const ms = expiresAtMs(session);
  if (ms == null) return true;
  return ms < Date.now() + bufferMs;
}
