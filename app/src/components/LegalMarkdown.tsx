import React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import type { AppColors } from "@/theme/colors";

export function LegalMarkdown({
  markdown,
  colors,
}: {
  markdown: string;
  colors: AppColors;
}) {
  const lines = (markdown || "").split("\n");
  return (
    <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
      {lines.map((line, i) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <View key={`sp-${i}`} style={{ height: 10 }} />;
        }
        const isTitle = trimmed.startsWith("## ");
        const isSub = trimmed.startsWith("### ");
        const text = trimmed
          .replace(/^#+\s*/, "")
          .replace(/\*\*/g, "")
          .replace(/^-\s*/, "• ");
        return (
          <Text
            key={`ln-${i}`}
            style={[
              styles.base,
              { color: colors.text },
              isTitle && [styles.title, { color: colors.text }],
              isSub && [styles.sub, { color: colors.textMuted }],
            ]}
          >
            {text}
          </Text>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1 },
  content: { padding: 20, paddingBottom: 40 },
  base: { fontSize: 15, lineHeight: 22, marginBottom: 6 },
  title: { fontSize: 22, fontWeight: "800", marginBottom: 12, marginTop: 4 },
  sub: { fontSize: 17, fontWeight: "700", marginTop: 8, marginBottom: 6 },
});
