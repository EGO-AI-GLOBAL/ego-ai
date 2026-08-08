/** Fases do monstrinho (espelha PET_STAGES em ego_api/daily_care.py). */
export type MoodPetStageKey =
  | "filhote"
  | "jovem"
  | "crescido"
  | "guardiao"
  | "lendario"
  | "mistico";

export type MoodPetStageStyle = {
  /** Moldura do palco. */
  border: string;
  /** Faixa/aura por trás da legenda. */
  aura: string;
  /** Cor do texto do selo da fase. */
  badgeText: string;
  /** Fundo do selo da fase. */
  badgeBg: string;
};

const STAGE_STYLES: Record<MoodPetStageKey, MoodPetStageStyle> = {
  filhote: {
    border: "#5A9E62",
    aura: "rgba(255,255,255,0.55)",
    badgeText: "#1a3d1a",
    badgeBg: "rgba(255,255,255,0.75)",
  },
  jovem: {
    border: "#3FA6A0",
    aura: "rgba(214,247,245,0.60)",
    badgeText: "#0d3d3a",
    badgeBg: "rgba(214,247,245,0.85)",
  },
  crescido: {
    border: "#3B86C7",
    aura: "rgba(214,236,255,0.60)",
    badgeText: "#0c3355",
    badgeBg: "rgba(214,236,255,0.85)",
  },
  guardiao: {
    border: "#7B5FD1",
    aura: "rgba(232,224,255,0.60)",
    badgeText: "#2a1a5e",
    badgeBg: "rgba(232,224,255,0.85)",
  },
  lendario: {
    border: "#D19A2E",
    aura: "rgba(255,240,205,0.65)",
    badgeText: "#5c3d00",
    badgeBg: "rgba(255,240,205,0.9)",
  },
  mistico: {
    border: "#C94B92",
    aura: "rgba(255,224,241,0.65)",
    badgeText: "#5c0f3d",
    badgeBg: "rgba(255,224,241,0.9)",
  },
};

export function petStageStyle(stageKey?: string | null): MoodPetStageStyle {
  const key = (stageKey || "").trim().toLowerCase() as MoodPetStageKey;
  return STAGE_STYLES[key] ?? STAGE_STYLES.filhote;
}

/** Nome a mostrar no palco: nome próprio, senão o humor. */
export function petDisplayName(petName?: string | null, moodLabel?: string): string {
  const name = (petName || "").trim();
  if (name) return name;
  return moodLabel || "Monstrinho";
}
