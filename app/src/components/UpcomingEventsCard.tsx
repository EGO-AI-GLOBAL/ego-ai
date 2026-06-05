import React from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import type { AppColors } from "@/theme/colors";
import type { UpcomingItem } from "@/utils/upcomingEvents";

type Props = {
  colors: AppColors;
  items: UpcomingItem[];
  onPressItem?: (item: UpcomingItem) => void;
};

export function UpcomingEventsCard({ colors, items, onPressItem }: Props) {
  if (!items.length) return null;
  return (
    <View style={styles.wrap}>
      <Text style={[styles.title, { color: colors.textMuted }]}>Próximos</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
        {items.map((item) => (
          <Pressable
            key={item.id}
            onPress={() => onPressItem?.(item)}
            style={({ pressed }) => [
              styles.card,
              {
                backgroundColor: colors.bgCard,
                borderColor: colors.border,
                opacity: pressed ? 0.9 : 1,
              },
            ]}
          >
            <Text style={[styles.eventTitle, { color: colors.text }]} numberOfLines={1}>
              {item.title}
            </Text>
            <Text style={[styles.when, { color: colors.textMuted }]} numberOfLines={1}>
              {item.whenLabel}
            </Text>
          </Pressable>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: 8 },
  title: { fontSize: 12, fontWeight: "600", marginBottom: 6 },
  row: { gap: 8 },
  card: {
    width: 150,
    borderRadius: 10,
    borderWidth: StyleSheet.hairlineWidth,
    padding: 10,
  },
  eventTitle: { fontSize: 14, fontWeight: "700" },
  when: { fontSize: 12, marginTop: 4 },
});
