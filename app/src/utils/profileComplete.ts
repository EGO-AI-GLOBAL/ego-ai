import type { MeData } from "@/api/types";

export function profilePhoneFromMe(me: MeData | null | undefined): string {
  const profile = me?.profile as Record<string, unknown> | undefined;
  return typeof profile?.phone === "string" ? profile.phone.trim() : "";
}

export function isProfilePhoneMissing(me: MeData | null | undefined): boolean {
  return !profilePhoneFromMe(me);
}
