import React from "react";
import { Platform, StyleSheet, Text, View } from "react-native";
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
              isUser ? styles.user : styles.assistant,
              {
                backgroundColor: isUser ? colors.primaryTint : colors.glassBg,
                borderColor: isUser ? colors.primarySoft : colors.glassBorder,
                shadowColor: isUser ? colors.primary : colors.glowCyan,
              },
            ]}
          >
            <Text style={[styles.role, { color: colors.textMuted }]}>
              {isUser ? "Você" : assistantLabel}
            </Text>
            <Text style={[styles.text, { color: colors.text }]} selectable>
              {m.content}
            </Text>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  list: { gap: 14, paddingBottom: 8, paddingHorizontal: 2 },
  bubble: {
    borderRadius: 20,
    paddingVertical: 12,
    paddingHorizontal: 16,
    maxWidth: "92%",
    borderWidth: 1,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.14,
    shadowRadius: 8,
    elevation: 2,
    ...(Platform.OS === "web" ? ({ backdropFilter: "blur(8px)" } as object) : {}),
  },
  user: { alignSelf: "flex-end" },
  assistant: { alignSelf: "flex-start" },
  role: {
    fontSize: 10,
    textTransform: "uppercase",
    marginBottom: 6,
    letterSpacing: 0.5,
    fontWeight: "700",
  },
  text: {
    fontSize: 15,
    lineHeight: 22,
    letterSpacing: 0.1,
  },
});
