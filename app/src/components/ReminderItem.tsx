import React, { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { createShoppingItem, patchShoppingItem } from "@/api/client";
import type { AppColors } from "@/theme/colors";
import type { Reminder, ShoppingListItem } from "@/api/types";
import { formatScheduledLocal } from "@/utils/scheduleTime";

export function ReminderItem({
  item,
  colors,
  onDismiss,
  onShoppingChange,
}: {
  item: Reminder;
  colors: AppColors;
  onDismiss?: (id: string) => void;
  onShoppingChange?: () => Promise<void>;
}) {
  const id = String(item.id || "");
  const shopping = item.shopping_items || [];
  const [expanded, setExpanded] = useState(shopping.length > 0);
  const [newItem, setNewItem] = useState("");
  const [saving, setSaving] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);

  const onToggleItem = async (shop: ShoppingListItem) => {
    const sid = String(shop.id || "");
    if (!sid || !onShoppingChange) return;
    setToggling(sid);
    try {
      await patchShoppingItem(sid, { done: true });
      await onShoppingChange();
    } finally {
      setToggling(null);
    }
  };

  const onAddItem = async () => {
    const t = newItem.trim();
    if (!t || !id || !onShoppingChange) return;
    setSaving(true);
    try {
      await createShoppingItem({ title: t, reminder_id: id, category: "mercado" });
      setNewItem("");
      setExpanded(true);
      await onShoppingChange();
    } finally {
      setSaving(false);
    }
  };

  return (
    <View style={[styles.row, { borderBottomColor: colors.border }]}>
      <View style={[styles.dot, { backgroundColor: colors.primary }]} />
      <View style={styles.body}>
        <Pressable onPress={() => setExpanded((v) => !v)} disabled={!onShoppingChange}>
          <Text style={[styles.title, { color: colors.text }]} numberOfLines={2}>
            {item.title || "Lembrete"}
          </Text>
          <Text style={[styles.when, { color: colors.textMuted }]}>
            {formatScheduledLocal(item.scheduled_at)}
            {shopping.length > 0 ? ` · ${shopping.length} na lista` : ""}
          </Text>
        </Pressable>
        {expanded && onShoppingChange ? (
          <View style={styles.shopBox}>
            {shopping.map((shop) => {
              const sid = String(shop.id || "");
              return (
                <Pressable
                  key={sid}
                  onPress={() => onToggleItem(shop)}
                  disabled={toggling === sid}
                  style={styles.shopRow}
                >
                  <View style={[styles.checkbox, { borderColor: colors.primary }]} />
                  <Text style={{ color: colors.text, flex: 1, fontSize: 14 }}>
                    {shop.title || "Item"}
                  </Text>
                  {toggling === sid ? (
                    <ActivityIndicator size="small" color={colors.primary} />
                  ) : null}
                </Pressable>
              );
            })}
            <View style={styles.addRow}>
              <TextInput
                value={newItem}
                onChangeText={setNewItem}
                placeholder="Leite, sabão…"
                placeholderTextColor={colors.textMuted}
                style={[
                  styles.addInput,
                  { color: colors.text, borderColor: colors.border, backgroundColor: colors.bg },
                ]}
              />
              <Pressable
                onPress={onAddItem}
                disabled={saving || !newItem.trim()}
                style={[styles.addBtn, { backgroundColor: colors.primary }]}
              >
                {saving ? (
                  <ActivityIndicator color="#fff" size="small" />
                ) : (
                  <Text style={styles.addBtnText}>+</Text>
                )}
              </Pressable>
            </View>
          </View>
        ) : null}
      </View>
      {onDismiss && id ? (
        <Pressable
          onPress={() => onDismiss(id)}
          style={[styles.delBtn, { borderColor: colors.border }]}
          accessibilityLabel="Apagar da agenda"
        >
          <Text style={[styles.delText, { color: colors.danger }]}>Apagar</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "flex-start",
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginTop: 6,
    marginRight: 12,
  },
  body: { flex: 1 },
  title: { fontSize: 15, fontWeight: "600" },
  when: { fontSize: 13, marginTop: 2 },
  shopBox: { marginTop: 8 },
  shopRow: { flexDirection: "row", alignItems: "center", paddingVertical: 4 },
  checkbox: {
    width: 18,
    height: 18,
    borderRadius: 4,
    borderWidth: 2,
    marginRight: 8,
  },
  addRow: { flexDirection: "row", gap: 8, marginTop: 6 },
  addInput: {
    flex: 1,
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    fontSize: 14,
  },
  addBtn: {
    paddingHorizontal: 12,
    borderRadius: 8,
    justifyContent: "center",
    alignItems: "center",
  },
  addBtnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  delBtn: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
  },
  delText: { fontSize: 12, fontWeight: "700" },
});
