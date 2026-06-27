import { api } from "@/api/client";
import type { WellnessJourney } from "@/api/types";

export const COMPANION_NAME_UI_KEY = "ego_companion_name";
export const COMPANION_NAME_SETUP_KEY = "ego_companion_name_setup_done";

const MAX_LEN = 20;

/** Nome curto e seguro para UI/push. */
export function sanitizeCompanionName(raw: string): string {
  const trimmed = raw.trim().replace(/\s+/g, " ");
  const clean = trimmed.replace(/[^\p{L}\p{N}\s'.-]/gu, "");
  return clean.slice(0, MAX_LEN);
}

export function resolveCompanionDisplayName(journey: WellnessJourney): string {
  const custom = sanitizeCompanionName(journey.companion_name ?? "");
  if (custom) return custom;
  return (journey.companion_stage_label ?? "EGO de Bolso").trim() || "EGO de Bolso";
}

export function companionNeedsNameSetup(journey: WellnessJourney): boolean {
  if (journey.companion_name_setup_done) return false;
  return !sanitizeCompanionName(journey.companion_name ?? "");
}

export async function saveCompanionName(raw: string): Promise<string> {
  const name = sanitizeCompanionName(raw);
  if (!name) {
    throw new Error("Digite um nome para o bolso");
  }
  await api.patch("profile", {
    ui_state: {
      [COMPANION_NAME_UI_KEY]: name,
      [COMPANION_NAME_SETUP_KEY]: true,
    },
  });
  return name;
}
