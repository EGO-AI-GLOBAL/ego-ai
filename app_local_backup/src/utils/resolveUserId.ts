import { getSession } from "@/api/client";
import type { AuthSession } from "@/api/types";

export function resolveUserId(
  session: AuthSession | null | undefined,
  meUserId?: string | null
): string {
  return (
    session?.user?.id?.trim() ||
    getSession()?.user?.id?.trim() ||
    meUserId?.trim() ||
    ""
  );
}
