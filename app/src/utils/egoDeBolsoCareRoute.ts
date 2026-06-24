import type { WellnessJourney } from "@/api/types";

export type EgoCareRoute = "/(main)/agenda" | "/(main)/daily-care" | "/(main)/chat";

function textHintsAgenda(text: string): boolean {
  const t = text.toLowerCase();
  return (
    t.includes("agenda") ||
    t.includes("hábito") ||
    t.includes("habito") ||
    t.includes("lembrete") ||
    t.includes("compromisso") ||
    t.includes("entre nós") ||
    t.includes("entre nos") ||
    t.includes("convite")
  );
}

function textHintsDailyCare(text: string): boolean {
  const t = text.toLowerCase();
  return (
    t.includes("check-in") ||
    t.includes("checkin") ||
    t.includes("monstrinho") ||
    t.includes("humor")
  );
}

/** Para onde enviar «Cuidar agora» conforme a missão do nível. */
export function resolveEgoDeBolsoCareRoute(journey: WellnessJourney): EgoCareRoute {
  const pending = journey.steps?.filter((s) => !s.done) ?? [];
  const task = journey.today_task ?? "";

  for (const step of pending) {
    const key = (step.key ?? "").toLowerCase();
    const label = step.label ?? "";

    if (key === "habit" || key === "reminder" || key === "invite" || key === "draft_confirm") {
      return "/(main)/agenda";
    }
    if (key === "checkin" || key === "streak") return "/(main)/daily-care";
    if (key === "night_dump") return "/(main)/chat";
    if (key === "chat" || key === "voice") return "/(main)/chat";

    if (key === "or") {
      if (textHintsAgenda(label)) return "/(main)/agenda";
      if (textHintsDailyCare(label)) return "/(main)/daily-care";
      if (label.toLowerCase().includes("desabafo")) return "/(main)/chat";
      if (label.toLowerCase().includes("chat") || label.toLowerCase().includes("voz")) {
        return "/(main)/chat";
      }
    }
  }

  if (textHintsAgenda(task)) return "/(main)/agenda";
  if (textHintsDailyCare(task)) return "/(main)/daily-care";
  return "/(main)/chat";
}
