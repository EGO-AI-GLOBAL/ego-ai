import { Linking, Platform, Share } from "react-native";

const PLAY_TESTING = "https://play.google.com/apps/testing/com.egoai.app";
const TESTFLIGHT = "https://testflight.apple.com/join/eNDKdFWF";

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

export function buildEntreNosInviteMessage(groupName: string): string {
  const name = (groupName || "Entre Nós").trim();
  return (
    `Oi! Criei nosso *Entre Nós* «${name}» no EGO-AI.\n\n` +
    `Baixe grátis:\n🤖 Android:\n${PLAY_TESTING}\n\n` +
    `🍎 iPhone:\n${TESTFLIGHT}\n\n` +
    `Entre com o mesmo telefone ou e-mail que eu usei no convite.`
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
  const line = opts.atRisk
    ? `🔥 Ofensiva em risco — ${opts.days} dia(s) com ${who}`
    : `🔥 ${opts.days} ${opts.days === 1 ? "dia" : "dias"} organizados com ${who}`;
  return (
    `${line}\n\nDesabafo → Agenda no EGO-AI.\n` +
    `Teste grátis:\n🤖 ${PLAY_TESTING}\n🍎 ${TESTFLIGHT}`
  );
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

export async function shareEntreNosInviteWhatsApp(groupName: string): Promise<void> {
  await shareWhatsAppText(buildEntreNosInviteMessage(groupName));
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
