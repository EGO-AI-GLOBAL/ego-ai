/** Paletas de cor do ovo — espelham ego_api/companion_shop.py EGG_COLOR_ITEMS */

export type CompanionEggPalette = {
  body: [string, string, string];
  ring: string;
  glow: string;
  accent: string;
};

export const DEFAULT_EGG_COLOR = "cosmic";

export const EGG_COLOR_PALETTES: Record<string, CompanionEggPalette> = {
  cosmic: {
    body: ["#1E0A3C", "#5B21B6", "#22D3EE"],
    ring: "#A78BFA",
    glow: "rgba(34, 211, 238, 0.45)",
    accent: "#E879F9",
  },
  rose: {
    body: ["#3B0A2E", "#BE185D", "#F472B6"],
    ring: "#F9A8D4",
    glow: "rgba(244, 114, 182, 0.45)",
    accent: "#FBCFE8",
  },
  emerald: {
    body: ["#052E16", "#047857", "#34D399"],
    ring: "#6EE7B7",
    glow: "rgba(52, 211, 153, 0.45)",
    accent: "#A7F3D0",
  },
  gold: {
    body: ["#422006", "#B45309", "#FCD34D"],
    ring: "#FDE68A",
    glow: "rgba(252, 211, 77, 0.45)",
    accent: "#FEF3C7",
  },
  sunset: {
    body: ["#431407", "#EA580C", "#FB923C"],
    ring: "#FDBA74",
    glow: "rgba(251, 146, 60, 0.45)",
    accent: "#FFEDD5",
  },
};

export function resolveEggPalette(colorId?: string | null): CompanionEggPalette {
  const key = String(colorId || DEFAULT_EGG_COLOR).trim().toLowerCase();
  return EGG_COLOR_PALETTES[key] ?? EGG_COLOR_PALETTES[DEFAULT_EGG_COLOR];
}
