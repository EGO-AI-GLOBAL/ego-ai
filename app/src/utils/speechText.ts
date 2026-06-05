/** Texto adequado para TTS (sem emojis nem markdown). */
export function plainTextForSpeech(text: string, maxLen = 3000): string {
  let t = (text || "").trim();
  if (!t) return "";
  t = t.replace(/\[\[EGO_[^\]]+\]\]/g, "");
  t = t.replace(/```[\s\S]*?```/g, " ");
  t = t.replace(/`([^`]+)`/g, "$1");
  t = t.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");
  t = t.replace(/[*_#>|]+/g, " ");
  t = t.replace(
    /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FAFF}\u{2600}-\u{27BF}\u200d\ufe0f]/gu,
    ""
  );
  t = t.replace(/\s+/g, " ").trim();
  return t.slice(0, maxLen);
}
