import type { PlanTier } from "@/api/types";

export type AvatarCategory = "female" | "male" | "neutral";
export type AvatarCollection = "professional" | "young" | "calm" | "energetic";
export type VoiceStyle = "warm" | "clear" | "calm" | "energetic";
export type AvatarEthnicity =
  | "afro-brazilian"
  | "asian-east"
  | "asian-south"
  | "arab-mena"
  | "black-african"
  | "latino"
  | "white-european"
  | "mixed"
  | "neutral";

export type AvatarCatalogEntry = {
  id: string;
  shortName: string;
  displayName: string;
  category: AvatarCategory;
  collection: AvatarCollection;
  voiceStyle: VoiceStyle;
  ethnicity: AvatarEthnicity;
  /** Regiões-alvo para ordenar sugestões por localidade futuramente */
  targetRegions: string[];
  avatar_id: string;
  voice_id: string;
  /** Nome da voz TTS (Edge) — única por avatar */
  voiceLabel: string;
  minPlan: PlanTier;
  /** Prompt para geração de imagem / briefing para designer */
  visualBrief: string;
};

const TIER_RANK: Record<PlanTier, number> = {
  essential: 0,
  connection: 1,
  premium: 2,
  total: 3,
  enterprise: 4,
};

/**
 * FASE 1 — 12 avatares: 2 grátis + 4 Conexão + 3 Premium + 3 Total.
 * FASE 2 — expandir para 24 quando tiver assets prontos para cada um.
 *
 * Lógica de desbloqueio:
 *   Essencial (free) → Luna + Leo
 *   Conexão → + Aisha + Hana + Kai + Omar
 *   Premium → + Amara + Ravi + Alex
 *   Total   → + Sara + Malik + Jordan
 */
export const AVATAR_CATALOG: AvatarCatalogEntry[] = [
  // ── GRÁTIS ──────────────────────────────────────────────
  {
    id: "f1",
    shortName: "Luna",
    displayName: "Luna",
    category: "female",
    collection: "calm",
    voiceStyle: "warm",
    ethnicity: "latino",
    targetRegions: ["BR", "LATAM"],
    avatar_id: "f1",
    voice_id: "vf1",
    voiceLabel: "Francisca (BR)",
    minPlan: "essential",
    visualBrief:
      "Mulher brasileira latina, ~26 anos, pele cor mel, cabelos cacheados ruivos/cobreados médios, olhos castanhos calorosos, suéter terracota ou verde-sálvia, fundo minimalista sage green, expressão acolhedora e serena, estilo original EGO-AI (não copiar referências externas).",
  },
  {
    id: "m1",
    shortName: "Leo",
    displayName: "Leo",
    category: "male",
    collection: "professional",
    voiceStyle: "clear",
    ethnicity: "latino",
    targetRegions: ["BR", "LATAM"],
    avatar_id: "m1",
    voice_id: "vm1",
    voiceLabel: "António (BR)",
    minPlan: "essential",
    visualBrief:
      "Homem latino (colombiano-brasileiro), ~29 anos, pele caramelo, cabelo curto fade com topo ondulado, rosto limpo ou barba de um dia, camisa chambray azul clara de mangas arregaçadas, fundo desfocado de café/clara, sorriso confiante, visual original EGO-AI.",
  },

  // ── CONEXÃO ─────────────────────────────────────────────
  {
    id: "f2",
    shortName: "Aisha",
    displayName: "Aisha",
    category: "female",
    collection: "professional",
    voiceStyle: "clear",
    ethnicity: "arab-mena",
    targetRegions: ["MENA", "EU", "NA"],
    avatar_id: "f2",
    voice_id: "vf2",
    voiceLabel: "Salma (árabe)",
    minPlan: "connection",
    visualBrief:
      "Mulher árabe-mediterrânea (Líbano/Egito), ~33 anos, pele oliva, cabelo castanho escuro ondulado até os ombros, brincos dourados discretos, blazer azul-petróleo moderno, fundo creme com sombra geométrica suave, expressão serena e profissional, visual original EGO-AI.",
  },
  {
    id: "f3",
    shortName: "Hana",
    displayName: "Hana",
    category: "female",
    collection: "young",
    voiceStyle: "energetic",
    ethnicity: "asian-east",
    targetRegions: ["JP", "KR", "SEA", "NA"],
    avatar_id: "f3",
    voice_id: "vf3",
    voiceLabel: "Nanami (asiática)",
    minPlan: "connection",
    visualBrief:
      "Mulher leste-asiática, ~24 anos, pele clara, cabelo preto curto com franja, sorriso alegre, maquiagem leve, roupa jovem colorida, fundo branco limpo com detalhe colorido.",
  },
  {
    id: "m2",
    shortName: "Kai",
    displayName: "Kai",
    category: "male",
    collection: "energetic",
    voiceStyle: "energetic",
    ethnicity: "mixed",
    targetRegions: ["SEA", "NA", "EU"],
    avatar_id: "m2",
    voice_id: "vm2",
    voiceLabel: "Brian (jovem)",
    minPlan: "connection",
    visualBrief:
      "Homem jovem miscigenado (traços sul-americano + asiático), ~25 anos, pele média, cabelo preto com leve textura, sorriso grande, moletom ou hoodie casual, fundo urbano desfocado.",
  },
  {
    id: "m3",
    shortName: "Omar",
    displayName: "Omar",
    category: "male",
    collection: "calm",
    voiceStyle: "calm",
    ethnicity: "arab-mena",
    targetRegions: ["MENA", "EU", "AF"],
    avatar_id: "m3",
    voice_id: "vm3",
    voiceLabel: "Shakir (árabe)",
    minPlan: "connection",
    visualBrief:
      "Homem árabe, ~38 anos, pele morena escura, barba bem cuidada, olhos escuros, expressão calma e madura, camisa social azul marinho, fundo bege claro, iluminação natural lateral.",
  },

  // ── PREMIUM ─────────────────────────────────────────────
  {
    id: "f4",
    shortName: "Amara",
    displayName: "Amara",
    category: "female",
    collection: "calm",
    voiceStyle: "warm",
    ethnicity: "black-african",
    targetRegions: ["AF", "EU", "NA", "BR"],
    avatar_id: "f4",
    voice_id: "vf4",
    voiceLabel: "Ava (calorosa)",
    minPlan: "premium",
    visualBrief:
      "Mulher negra africana, ~30 anos, pele negra profunda, cabelo natural afro volumoso, sorriso caloroso, brincos simples, blusa colorida com estampa sutil, fundo com luz quente dourada.",
  },
  {
    id: "m4",
    shortName: "Ravi",
    displayName: "Ravi",
    category: "male",
    collection: "professional",
    voiceStyle: "clear",
    ethnicity: "asian-south",
    targetRegions: ["IN", "SEA", "EU", "NA"],
    avatar_id: "m4",
    voice_id: "vm4",
    voiceLabel: "Madhur (índia)",
    minPlan: "premium",
    visualBrief:
      "Homem sul-asiático (indiano), ~35 anos, pele morena escura, cabelo escuro bem cortado, barba curta, expressão intelectual e amigável, camisa polo ou social, fundo neutro acinzentado.",
  },
  {
    id: "g1",
    shortName: "Alex",
    displayName: "Alex",
    category: "neutral",
    collection: "young",
    voiceStyle: "warm",
    ethnicity: "mixed",
    targetRegions: ["Global"],
    avatar_id: "g1",
    voice_id: "vg1",
    voiceLabel: "Seraphina (neutra)",
    minPlan: "premium",
    visualBrief:
      "Pessoa não-binária, ~27 anos, pele clara-média, cabelo curto platinado ou colorido nas pontas, estilo andrógino moderno, expressão aberta e acolhedora, camiseta com mensagem positiva sutil, fundo colorido pastel.",
  },

  // ── TOTAL ────────────────────────────────────────────────
  {
    id: "f5",
    shortName: "Sara",
    displayName: "Sara",
    category: "female",
    collection: "professional",
    voiceStyle: "clear",
    ethnicity: "white-european",
    targetRegions: ["EU", "NA", "BR"],
    avatar_id: "f5",
    voice_id: "vf5",
    voiceLabel: "Raquel (PT)",
    minPlan: "total",
    visualBrief:
      "Mulher europeia, ~40 anos, pele clara, cabelo loiro ou castanho claro liso, expressão madura e elegante, blazer neutro, acessório discreto, fundo escritório moderno desfocado.",
  },
  {
    id: "m5",
    shortName: "Malik",
    displayName: "Malik",
    category: "male",
    collection: "energetic",
    voiceStyle: "energetic",
    ethnicity: "afro-brazilian",
    targetRegions: ["BR", "AF", "EU", "NA"],
    avatar_id: "m5",
    voice_id: "vm5",
    voiceLabel: "Hyunsu (urbano)",
    minPlan: "total",
    visualBrief:
      "Homem afro-brasileiro, ~28 anos, pele negra, cabelo dread curto ou crespo volumoso, sorriso confiante, moletom streetwear moderno, cordão discreto, fundo urbano vibrante.",
  },
  {
    id: "g2",
    shortName: "Jordan",
    displayName: "Jordan",
    category: "neutral",
    collection: "calm",
    voiceStyle: "calm",
    ethnicity: "neutral",
    targetRegions: ["Global"],
    avatar_id: "g2",
    voice_id: "vg2",
    voiceLabel: "Vivienne (neutra)",
    minPlan: "total",
    visualBrief:
      "Pessoa não-binária, ~32 anos, pele média-escura, cabelo preto ondulado médio, óculos modernos finos, expressão serena e reflexiva, camisa desabotoada em cima de camiseta branca, fundo biblioteca ou natureza desfocada.",
  },
];

// ─── Labels ──────────────────────────────────────────────────────────────────

export const AVATAR_CATEGORY_LABELS: Record<AvatarCategory, string> = {
  female: "Feminino",
  male: "Masculino",
  neutral: "Diversidade",
};

export const AVATAR_COLLECTION_LABELS: Record<AvatarCollection, string> = {
  professional: "Profissional",
  young: "Jovem",
  calm: "Calmo",
  energetic: "Enérgico",
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

export function normalizePlanTier(tier?: string | null): PlanTier {
  const t = (tier || "essential").trim().toLowerCase();
  if (!t) return "essential";
  const aliases: Record<string, PlanTier> = {
    free: "essential",
    gratis: "essential",
    grátis: "essential",
    essencial: "essential",
    "ego essencial": "essential",
    conexao: "connection",
    conexão: "connection",
    "ego conexao": "connection",
    "ego conexão": "connection",
    plus: "connection",
    pro: "connection",
    premium: "premium",
    "ego premium": "premium",
    vip: "total",
    total: "total",
    "ego total": "total",
    "plano total": "total",
    empresa: "enterprise",
    business: "enterprise",
    corporate: "enterprise",
    enterprise: "enterprise",
    "ego empresa": "enterprise",
    connection: "connection",
  };
  if (aliases[t]) return aliases[t];
  if (t.includes("enterprise") || t.includes("empresa")) return "enterprise";
  if (t.includes("total")) return "total";
  if (t.includes("premium")) return "premium";
  if (t.includes("conex") || t.includes("connection")) return "connection";
  if (t.includes("essencial") || t.includes("essential") || t.includes("gratis"))
    return "essential";
  return "essential";
}

/** Plano efetivo para desbloquear avatares (espelha API + contas de teste). */
export function effectiveAvatarPlanTier(
  access?: { plan_tier?: string | null; is_test_total?: boolean } | null
): PlanTier {
  if (access?.is_test_total) return "total";
  return normalizePlanTier(access?.plan_tier);
}

export function isAvatarUnlocked(
  userTier: PlanTier | string | undefined,
  entry: AvatarCatalogEntry
): boolean {
  const u = normalizePlanTier(userTier);
  return TIER_RANK[u] >= TIER_RANK[entry.minPlan];
}

export function planLabelForAvatar(minPlan: PlanTier): string {
  switch (minPlan) {
    case "essential":
      return "Grátis";
    case "connection":
      return "Plano Conexão";
    case "premium":
      return "Plano Premium";
    case "total":
      return "Plano Total";
    case "enterprise":
      return "Plano Empresa";
    default:
      return "Assinar";
  }
}

export function findAvatarInCatalog(avatarId?: string): AvatarCatalogEntry | undefined {
  const id = (avatarId || "f1").toLowerCase();
  return AVATAR_CATALOG.find((a) => a.avatar_id === id);
}

export function avatarsByCategory(category: AvatarCategory): AvatarCatalogEntry[] {
  return AVATAR_CATALOG.filter((a) => a.category === category);
}

export function avatarsByCollection(collection: AvatarCollection): AvatarCatalogEntry[] {
  return AVATAR_CATALOG.filter((a) => a.collection === collection);
}
