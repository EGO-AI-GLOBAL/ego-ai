import React from "react";
import { StyleSheet, Text, View } from "react-native";
import type { ChatMessage } from "@/api/types";
import { useColors } from "@/theme/ThemeContext";

type Props = {
  messages: ChatMessage[];
  assistantLabel?: string;
};

export function ChatPreview({ messages, assistantLabel = "Assistente" }: Props) {
  const colors = useColors();
  if (!messages.length) return null;

  return (
    <View style={styles.list}>
      {messages.map((m, i) => {
        const isUser = m.role === "user";
        return (
          <View
            key={`${m.msg_id || i}-${m.role}-${i}`}
            style={[
              styles.bubble,
              {
                backgroundColor: isUser ? colors.userBubble : colors.assistantBubble,
                borderColor: colors.border,
              },
              isUser ? styles.user : styles.assistant,
            ]}
          >
            <Text style={[styles.role, { color: colors.textMuted }]}>
              {isUser ? "Você" : assistantLabel}
            </Text>
            <Text
              style={[styles.text, { color: colors.text }]}
              selectable
            >
              {m.content}
            </Text>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  list: { gap: 12, paddingBottom: 4 },
  bubble: {
    borderRadius: 16,
    paddingVertical: 12,
    paddingHorizontal: 14,
    maxWidth: "96%",
    borderWidth: StyleSheet.hairlineWidth,
  },
  user: { alignSelf: "flex-end" },
  assistant: { alignSelf: "flex-start" },
  role: {
    fontSize: 11,
    textTransform: "uppercase",
    marginBottom: 6,
    letterSpacing: 0.4,
    fontWeight: "600",
  },
  text: {
    fontSize: 15,
    lineHeight: 22,
    letterSpacing: 0.1,
  },
});
