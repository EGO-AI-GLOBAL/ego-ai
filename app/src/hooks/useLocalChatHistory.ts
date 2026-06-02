import { useCallback, useEffect, useState } from "react";
import type { ChatMessage } from "@/api/types";
import {
  appendLocalChatExchange,
  buildApiHistoryContext,
  importLocalChatHistory,
  loadLocalChatHistory,
} from "@/storage/chatHistoryLocal";

export function useLocalChatHistory(userId: string, serverMessages: ChatMessage[]) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setReady(false);
    void (async () => {
      if (!userId.trim()) {
        if (!cancelled) {
          setMessages([]);
          setReady(true);
        }
        return;
      }
      const local = await loadLocalChatHistory(userId);
      if (!cancelled) {
        setMessages(local);
        setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [userId]);

  useEffect(() => {
    if (!userId.trim() || serverMessages.length === 0) return;
    void importLocalChatHistory(userId, serverMessages).then((merged) => {
      setMessages((prev) => (prev.length ? prev : merged));
    });
  }, [userId, serverMessages.length]);

  const historyForApi = useCallback(
    (excludePending = true) => {
      const base =
        excludePending && messages.length
          ? messages.filter((m) => m.content !== "…")
          : messages;
      return buildApiHistoryContext(base);
    },
    [messages]
  );

  const saveExchange = useCallback(
    async (userContent: string, assistantContent: string, opts?: { userWasVoice?: boolean }) => {
      if (!userId.trim()) return;
      const next = await appendLocalChatExchange(
        userId,
        userContent,
        assistantContent,
        opts
      );
      setMessages(next);
    },
    [userId]
  );

  return { messages, setMessages, ready, historyForApi, saveExchange };
}
