import { Linking, Platform, Share } from "react-native";

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
