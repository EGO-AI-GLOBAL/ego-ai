import type { MeData } from "@/api/types";

export function profilePhoneFromMe(me: MeData | null | undefined): string {
  const profile = me?.profile as Record<string, unknown> | undefined;
  return typeof profile?.phone === "string" ? profile.phone.trim() : "";
}

export function hasProfilePhone(
  me: MeData | null | undefined,
  localPhone?: string | null
): boolean {
  if (localPhone?.trim()) return true;
  return Boolean(profilePhoneFromMe(me));
}

export function isProfilePhoneMissing(
  me: MeData | null | undefined,
  localPhone?: string | null
): boolean {
  return !hasProfilePhone(me, localPhone);
}
