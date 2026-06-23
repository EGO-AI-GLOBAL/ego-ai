import { Linking, Platform, Share } from "react-native";
import type { DailyCareInfo, WellnessJourney } from "@/api/types";
import { inviteDownloadUrl, smartDownloadUrl } from "@/utils/appDownloadLink";
import { buildSocialFollowBlock } from "@/constants/socialProfiles";

const PLAY_TESTING = "https://play.google.com/apps/testing/com.egoai.app";
const TESTFLIGHT = "https://testflight.apple.com/join/eNDKdFWF";

/** Um link só: tenta abrir o app; senão Play ou TestFlight + cadastro. */
export function buildAppDownloadLinksBlock(opts?: { invite?: boolean }): string {
  const url = opts?.invite
    ? inviteDownloadUrl()
    : smartDownloadUrl({ campaign: "share" });
  return (
    `📲 Baixe grátis, faça cadastro e entre:\n` +
    `👉 ${url}\n\n` +
    `(Toque no link — Android ou iPhone, automático)`
  );
}

export const APP_DOWNLOAD_LINKS = {
  android: PLAY_TESTING,
  ios: TESTFLIGHT,
} as const;

export function buildEventWhatsAppMessage(opts: {
  calendarName: string;
  title: string;
  whenLabel: string;
  assistantName?: string;
}): string {
  const cal = (opts.calendarName || "Agenda").trim();
  const title = (opts.title || "Compromisso").trim();
  const when = (opts.whenLabel || "").trim();
  const who = (opts.assistantName || "EGO-AI").trim();
  let msg = `📅 *${cal}*\n${title}`;
  if (when) msg += `\n🕐 ${when}`;
  msg += `\n\nMarcado com ${who}. Confirma?`;
  return msg;
}

export function buildEntreNosInviteMessage(
  groupName: string,
  contactHint?: string
): string {
  return buildSharedCalendarInviteMessage(groupName, "entre_nos", contactHint);
}

export function buildSharedCalendarInviteMessage(
  calendarName: string,
  kind: "entre_nos" | "grupo" = "grupo",
  contactHint?: string
): string {
  const name = (calendarName || (kind === "entre_nos" ? "Entre Nós" : "nossa agenda")).trim();
  const intro =
    kind === "entre_nos"
      ? `Oi! Criei nosso *Entre Nós* «${name}» no EGO-AI.`
      : `Oi! Te convidei para a agenda *${name}* no EGO-AI.`;
  const hint = (contactHint || "").trim();
  const contactLine = hint
    ? `\n\nNo cadastro, use *exatamente* este contacto:\n${hint}`
    : "\n\nEntre com o mesmo telefone ou e-mail que eu usei no convite.";
  const afterLinks =
    kind === "entre_nos"
      ? "\n\nDepois abra *Agenda → Entre Nós* e toque em *Aceitar*."
      : "\n\nDepois abra *Agenda → Compartilhada* e toque em *Aceitar*.";
  return (
    `${intro}\n\n` +
    `${buildAppDownloadLinksBlock({ invite: true })}` +
    contactLine +
    afterLinks
  );
}

export function buildEntreNosEventMessage(opts: {
  groupName: string;
  title: string;
  whenLabel: string;
}): string {
  const group = (opts.groupName || "Entre Nós").trim();
  const title = (opts.title || "Compromisso").trim();
  const when = (opts.whenLabel || "").trim();
  let msg = `📅 *Entre Nós · ${group}*\n${title}`;
  if (when) msg += `\n🕐 ${when}`;
  msg += `\n\nConfirma ou recusa no app EGO-AI — sem "viu?" aqui 😅`;
  return msg;
}

export function buildStreakShareText(opts: {
  days: number;
  atRisk: boolean;
  assistantName?: string;
}): string {
  const who = (opts.assistantName || "Luna").trim();
  const days = Math.max(1, opts.days);
  const headline = opts.atRisk
    ? `🔥 Ofensiva em risco — estou com ${days} dia(s) com ${who}`
    : `🔥 Estou com ${days} ${days === 1 ? "dia" : "dias"} no EGO-AI com ${who}`;
  return (
    `${headline}\n\n` +
    `Desafio gratuito de bem-estar 💜\n` +
    `Quantos dias VOCÊ aguenta?\n\n` +
    `👉 Responde aqui com só o número (ex: 3, 7 ou 14) 🔥\n\n` +
    buildAppDownloadLinksBlock() +
    `\n\n` +
    buildSocialFollowBlock()
  );
}

/** Texto curto para legenda ao partilhar o cartão em Stories (imagem + links na legenda). */
export function buildStreakStoriesCaption(opts: {
  days: number;
  atRisk: boolean;
  assistantName?: string;
}): string {
  return buildStreakShareText(opts);
}

export function buildWellnessJourneyShareText(journey: WellnessJourney): string {
  const level = journey.level ?? 1;
  const title = (journey.title || "Jornada de Cuidado").trim();
  const emoji = journey.emoji || "💜";
  const headline = (
    journey.share_challenge ||
    `Nível ${level} ${emoji} ${title} — Jornada de Cuidado EGO-AI`
  ).trim();
  return (
    `${headline}\n\n` +
    `Eu estou no nível ${level}. E você?\n\n` +
    `Jogo grátis de bem-estar — começa fácil e vai subindo.\n` +
    `👉 Responde com seu nível (ex: 2, 5 ou 10) 🔥\n\n` +
    buildAppDownloadLinksBlock() +
    `\n\n` +
    buildSocialFollowBlock()
  );
}

export async function shareWellnessJourneyWhatsApp(journey: WellnessJourney): Promise<void> {
  await shareWhatsAppText(buildWellnessJourneyShareText(journey));
}

export function buildDailyCareShareText(care: DailyCareInfo): string {
  const days = Math.max(1, care.current ?? 1);
  const emoji = care.last_mood_emoji || "💜";
  const rank = care.ranking;
  const tierLine = rank
    ? `Ranking: ${rank.tier_emoji} ${rank.tier_label} (${days} dias)`
    : `${days} dias seguidos`;
  const top = rank?.community_top_days ?? 21;
  return (
    `💜 Desafio Diário EGO-AI\n\n` +
    `${tierLine}\n` +
    `Hoje: ${emoji}\n` +
    `Top da comunidade: ${top} dias — quantos VOCÊ aguenta?\n\n` +
    `👉 Responde com só o número 🔥\n\n` +
    buildAppDownloadLinksBlock({ campaign: "daily_care" }) +
    `\n\n` +
    buildSocialFollowBlock()
  );
}

export async function shareDailyCareWhatsApp(care: DailyCareInfo): Promise<void> {
  await shareWhatsAppText(buildDailyCareShareText(care));
}

export async function shareDailyCareStories(
  care: DailyCareInfo,
  imageUri?: string
): Promise<void> {
  const message = buildDailyCareShareText(care);
  try {
    if (imageUri) {
      await Share.share({ url: imageUri, message });
      return;
    }
    await Share.share({ message, title: "Desafio Diário EGO-AI" });
  } catch {
    /* cancelado */
  }
}

/** Partilhar legenda no TikTok (sheet nativo — utilizador escolhe TikTok). */
export async function shareDailyCareTikTok(care: DailyCareInfo): Promise<void> {
  const message = buildDailyCareShareText(care);
  try {
    await Share.share({ message, title: "Desafio Diário EGO-AI" });
  } catch {
    /* cancelado */
  }
}

/** Instagram / Stories — imagem opcional + legenda com links clicáveis. */
export async function shareWellnessJourneyNative(
  journey: WellnessJourney,
  imageUri?: string
): Promise<void> {
  const message = buildWellnessJourneyShareText(journey);
  try {
    if (imageUri) {
      await Share.share({ url: imageUri, message });
      return;
    }
    await Share.share({ message, title: "Desafio EGO-AI" });
  } catch {
    /* cancelado */
  }
}

export async function shareStreakStories(opts: {
  days: number;
  atRisk: boolean;
  assistantName?: string;
  imageUri?: string;
}): Promise<void> {
  const message = buildStreakStoriesCaption(opts);
  try {
    if (opts.imageUri) {
      await Share.share({ url: opts.imageUri, message });
      return;
    }
    await Share.share({ message, title: "Desafio EGO-AI" });
  } catch {
    /* cancelado */
  }
}

/** Partilha nativa (iOS/Android) — padrão de qualquer app sério. */
export async function shareEventMessage(opts: {
  calendarName: string;
  title: string;
  whenLabel: string;
  assistantName?: string;
}): Promise<void> {
  const message = buildEventWhatsAppMessage(opts);
  if (Platform.OS === "web") {
    await shareWhatsAppText(message);
    return;
  }
  try {
    await Share.share({ message, title: opts.title });
  } catch {
    /* utilizador cancelou */
  }
}

export async function shareEntreNosInviteWhatsApp(
  groupName: string,
  contactHint?: string
): Promise<void> {
  await shareWhatsAppText(buildEntreNosInviteMessage(groupName, contactHint));
}

export async function shareSharedCalendarInviteWhatsApp(
  calendarName: string,
  kind: "entre_nos" | "grupo" = "grupo",
  contactHint?: string
): Promise<void> {
  await shareWhatsAppText(buildSharedCalendarInviteMessage(calendarName, kind, contactHint));
}

/** Instagram, SMS, etc. — mesmo texto com links Play + TestFlight. */
export async function shareSharedCalendarInviteNative(
  calendarName: string,
  kind: "entre_nos" | "grupo" = "grupo",
  contactHint?: string
): Promise<void> {
  const message = buildSharedCalendarInviteMessage(calendarName, kind, contactHint);
  try {
    await Share.share({ message, title: "Convite EGO-AI" });
  } catch {
    /* cancelado */
  }
}

export async function shareEntreNosEventWhatsApp(opts: {
  groupName: string;
  title: string;
  whenLabel: string;
}): Promise<void> {
  await shareWhatsAppText(buildEntreNosEventMessage(opts));
}

export async function shareStreakWhatsApp(opts: {
  days: number;
  atRisk: boolean;
  assistantName?: string;
}): Promise<void> {
  await shareWhatsAppText(buildStreakShareText(opts));
}

export async function shareWhatsAppText(text: string): Promise<void> {
  const encoded = encodeURIComponent(text);
  const waUrl = `whatsapp://send?text=${encoded}`;
  const webUrl = `https://wa.me/?text=${encoded}`;
  try {
    if (Platform.OS === "web") {
      await Linking.openURL(webUrl);
      return;
    }
    const can = await Linking.canOpenURL(waUrl);
    if (can) {
      await Linking.openURL(waUrl);
      return;
    }
  } catch {
    /* fallback */
  }
  await Share.share({ message: text });
}
