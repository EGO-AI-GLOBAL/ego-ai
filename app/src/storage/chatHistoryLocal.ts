import AsyncStorage from "@react-native-async-storage/async-storage";
import type { ChatMessage } from "@/api/types";

const MAX_STORED_MESSAGES = 50;
const VOICE_LABEL = "Mensagem de voz";
const STORAGE_PREFIX = "ego_chat_history_v1_";

type StoredChatFile = {
  version: 1;
  messages: ChatMessage[];
};

function storageKey(userId: string): string {
  const safe = userId.replace(/[^a-zA-Z0-9_-]/g, "_");
  return `${STORAGE_PREFIX}${safe}`;
}

function trimMessages(messages: ChatMessage[]): ChatMessage[] {
  if (messages.length <= MAX_STORED_MESSAGES) {
    return messages;
  }
  return messages.slice(-MAX_STORED_MESSAGES);
}

function newMsgId(): string {
  return `local_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

function parseStored(raw: string | null): ChatMessage[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as StoredChatFile;
    if (!parsed?.messages || !Array.isArray(parsed.messages)) return [];
    return parsed.messages.filter(
      (m) =>
        (m.role === "user" || m.role === "assistant") &&
        typeof m.content === "string" &&
        m.content.trim().length > 0
    );
  } catch {
    return [];
  }
}

export async function loadLocalChatHistory(userId: string): Promise<ChatMessage[]> {
  if (!userId.trim()) return [];
  try {
    const raw = await AsyncStorage.getItem(storageKey(userId));
    return parseStored(raw);
  } catch {
    return [];
  }
}

async function persist(userId: string, messages: ChatMessage[]): Promise<void> {
  if (!userId.trim()) return;
  const payload: StoredChatFile = { version: 1, messages: trimMessages(messages) };
  await AsyncStorage.setItem(storageKey(userId), JSON.stringify(payload));
}

export async function appendLocalChatExchange(
  userId: string,
  userContent: string,
  assistantContent: string,
  opts?: { userWasVoice?: boolean }
): Promise<ChatMessage[]> {
  const existing = await loadLocalChatHistory(userId);
  const now = new Date().toISOString();
  const userText = opts?.userWasVoice ? VOICE_LABEL : userContent.trim();
  const next: ChatMessage[] = [
    ...existing,
    {
      role: "user",
      content: userText,
      msg_id: newMsgId(),
      created_at: now,
    },
    {
      role: "assistant",
      content: assistantContent.trim(),
      msg_id: newMsgId(),
      created_at: now,
    },
  ];
  await persist(userId, next);
  return next;
}

/** Mensagem só do assistente (guia de boas-vindas). */
export async function appendLocalAssistantMessage(
  userId: string,
  assistantContent: string,
  opts?: { onboarding?: boolean }
): Promise<ChatMessage[]> {
  const existing = await loadLocalChatHistory(userId);
  const now = new Date().toISOString();
  const next: ChatMessage[] = [
    ...existing,
    {
      role: "assistant",
      content: assistantContent.trim(),
      msg_id: opts?.onboarding
        ? `onboarding_${Date.now()}`
        : newMsgId(),
      created_at: now,
    },
  ];
  await persist(userId, next);
  return next;
}

export async function importLocalChatHistory(
  userId: string,
  messages: ChatMessage[]
): Promise<ChatMessage[]> {
  if (!userId.trim() || !messages.length) return loadLocalChatHistory(userId);
  const existing = await loadLocalChatHistory(userId);
  if (existing.length > 0) return existing;
  const normalized = trimMessages(
    messages.filter(
      (m) =>
        (m.role === "user" || m.role === "assistant") &&
        typeof m.content === "string" &&
        m.content.trim().length > 0
    )
  );
  await persist(userId, normalized);
  return normalized;
}

export async function clearLocalChatHistory(userId: string): Promise<void> {
  if (!userId.trim()) return;
  try {
    await AsyncStorage.removeItem(storageKey(userId));
  } catch {
    /* ignore */
  }
}

/** Últimos turnos para contexto da IA (sem a mensagem atual). */
export function buildApiHistoryContext(
  messages: ChatMessage[],
  maxTurns = 8
): { role: "user" | "assistant"; content: string }[] {
  const out: { role: "user" | "assistant"; content: string }[] = [];
  for (const m of messages) {
    if (m.role !== "user" && m.role !== "assistant") continue;
    if (m.msg_id?.startsWith("onboarding_")) continue;
    const content = (m.content || "").trim();
    if (!content || content === "…") continue;
    out.push({ role: m.role, content: content.slice(0, 8000) });
  }
  if (out.length <= maxTurns) return out;
  return out.slice(-maxTurns);
}
