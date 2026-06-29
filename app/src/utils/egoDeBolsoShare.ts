import type { WellnessJourney } from "@/api/types";
import { buildSocialFollowBlock } from "@/constants/socialProfiles";
import { egoDeBolsoDailyCarePercent } from "@/utils/egoDeBolsoDailyCare";
import { egoDeBolsoMissionsComplete } from "@/utils/egoDeBolsoCompanionMood";
import { resolveCompanionDisplayName } from "@/utils/egoDeBolsoCompanionName";

const PLAY_TESTING = "https://play.google.com/apps/testing/com.egoai.app";
const TESTFLIGHT = "https://testflight.apple.com/join/eNDKdFWF";

function buildAppDownloadLinksBlock(): string {
  return (
    `📲 Baixe grátis o EGO-AI:\n\n` +
    `🤖 Android (Google Play):\n${PLAY_TESTING}\n\n` +
    `🍎 iPhone (TestFlight):\n${TESTFLIGHT}\n\n` +
    `Toque no link do seu telefone 👆`
  );
}

function rebrandShareLine(text: string): string {
  return text
    .replace(/Jornada de Cuidado/gi, "EGO de Bolso")
    .replace(/Companheiro de Bolso/gi, "EGO de Bolso")
    .replace(/Desafio Diário/gi, "Monstrinhos do Humor");
}

export function pocketCompanionShareStats(journey: WellnessJourney) {
  const level = journey.level ?? 1;
  const max = journey.max_level ?? 500;
  const petName = resolveCompanionDisplayName(journey);
  const missionsToday = journey.missions_today ?? 0;
  const missionsPerDay = journey.missions_per_day ?? 5;
  const dayComplete = egoDeBolsoMissionsComplete(journey);
  const care = egoDeBolsoDailyCarePercent(journey);
  const stars = journey.stars ?? 0;
  const stageLabel = (journey.companion_stage_label ?? "Ovo").trim();
  const title = (journey.title || "EGO de Bolso").trim();
  const emoji = journey.emoji || "🥚";
  return {
    level,
    max,
    petName,
    missionsToday,
    missionsPerDay,
    dayComplete,
    care,
    stars,
    stageLabel,
    title,
    emoji,
  };
}

/** Linha principal do cartão visual (Stories / captura). */
export function pocketCompanionCardHeadline(journey: WellnessJourney): string {
  const s = pocketCompanionShareStats(journey);
  if (s.dayComplete) {
    return `Fechei ${s.missionsPerDay}/${s.missionsPerDay} missões hoje!`;
  }
  return `Nível ${s.level} · ${s.missionsToday}/${s.missionsPerDay} missões hoje`;
}

/** Desafio curto no cartão. */
export function pocketCompanionCardChallenge(journey: WellnessJourney): string {
  const s = pocketCompanionShareStats(journey);
  if (s.dayComplete) {
    return `Desafia: quem bate meu nível ${s.level} amanhã? 🥚`;
  }
  return `Desafia: responde com teu nível (ex: ${Math.max(1, s.level - 1)}, ${s.level} ou ${s.level + 1}) 🥚`;
}

/** Texto longo — WhatsApp e partilha geral. */
export function buildPocketCompanionWhatsAppText(journey: WellnessJourney): string {
  const s = pocketCompanionShareStats(journey);
  const headline = rebrandShareLine(
    (
      journey.share_challenge ||
      `Meu ${s.petName} está no nível ${s.level} ${s.emoji} — e o seu?`
    ).trim()
  );

  const progressLine = s.dayComplete
    ? `✅ ${s.missionsPerDay}/${s.missionsPerDay} missões hoje · cuidado ${s.care}%`
    : `📋 Missão de hoje: ${(journey.today_task || s.title).trim()}\n` +
      `Progresso: ${s.missionsToday}/${s.missionsPerDay} · cuidado ${s.care}%`;

  const starsLine = s.stars > 0 ? `\n⭐ ${s.stars} estrelas no bolso` : "";

  return (
    `${headline}\n\n` +
    `🥚 *${s.petName}* (${s.stageLabel}) — nível *${s.level}/${s.max}*\n` +
    `${progressLine}` +
    `${starsLine}\n\n` +
    `Tamagotchi de bem-estar no celular — anos 90 com IA 💜\n` +
    `👉 *Responde aqui só com teu nível* (número) ou manda print do teu bolso\n\n` +
    buildAppDownloadLinksBlock() +
    `\n\n` +
    buildSocialFollowBlock()
  );
}

/** Legenda curta — Instagram Stories / Post. */
export function buildPocketCompanionInstagramCaption(journey: WellnessJourney): string {
  const s = pocketCompanionShareStats(journey);
  const hook = s.dayComplete
    ? `Fechei o dia com ${s.petName} 🥚✨`
    : `${s.petName} pediu ajuda — nível ${s.level}`;

  return (
    `${hook}\n` +
    `${s.emoji} ${s.title}\n` +
    `${s.missionsToday}/${s.missionsPerDay} missões · ${s.care}% cuidado\n\n` +
    `Desafio: manda teu nível nos comentários ou no direct 🔥\n\n` +
    buildAppDownloadLinksBlock() +
    `\n\n` +
    buildSocialFollowBlock()
  );
}

/** Alias estável para SocialShareModal e exports antigos. */
export function buildPocketCompanionShareText(journey: WellnessJourney): string {
  return buildPocketCompanionWhatsAppText(journey);
}
