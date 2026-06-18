import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { createShoppingItem, deleteShoppingItem, patchShoppingItem } from "@/api/client";
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
  const doneCount = shopping.filter((s) => s.done).length;
  const [expanded, setExpanded] = useState(shopping.length > 0);
  const [newItem, setNewItem] = useState("");
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const onToggleItem = async (shop: ShoppingListItem) => {
    const sid = String(shop.id || "");
    if (!sid || !onShoppingChange) return;
    setBusyId(sid);
    try {
      await patchShoppingItem(sid, { done: !shop.done });
      await onShoppingChange();
    } finally {
      setBusyId(null);
    }
  };

  const onRemoveItem = (shop: ShoppingListItem) => {
    const sid = String(shop.id || "");
    if (!sid || !onShoppingChange) return;
    Alert.alert("Remover item", `Remover «${shop.title || "item"}» da lista?`, [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Remover",
        style: "destructive",
        onPress: async () => {
          setBusyId(sid);
          try {
            await deleteShoppingItem(sid);
            await onShoppingChange();
          } finally {
            setBusyId(null);
          }
        },
      },
    ]);
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
            {shopping.length > 0
              ? ` · ${doneCount} de ${shopping.length} na lista`
              : ""}
          </Text>
        </Pressable>
        {expanded && onShoppingChange ? (
          <View style={styles.shopBox}>
            {shopping.map((shop) => {
              const sid = String(shop.id || "");
              const isDone = !!shop.done;
              return (
                <View key={sid} style={styles.shopRow}>
                  <Pressable
                    onPress={() => onToggleItem(shop)}
                    disabled={busyId === sid}
                    style={styles.shopMain}
                  >
                    <View
                      style={[
                        styles.checkbox,
                        {
                          borderColor: colors.primary,
                          backgroundColor: isDone ? colors.primary : "transparent",
                        },
                      ]}
                    />
                    <Text
                      style={{
                        color: colors.text,
                        flex: 1,
                        fontSize: 14,
                        textDecorationLine: isDone ? "line-through" : "none",
                        opacity: isDone ? 0.65 : 1,
                      }}
                    >
                      {shop.title || "Item"}
                    </Text>
                    {busyId === sid ? (
                      <ActivityIndicator size="small" color={colors.primary} />
                    ) : null}
                  </Pressable>
                  <Pressable
                    onPress={() => onRemoveItem(shop)}
                    disabled={busyId === sid}
                    style={[styles.minusBtn, { borderColor: colors.border }]}
                    accessibilityLabel="Remover item da lista"
                  >
                    <Text style={{ color: colors.danger, fontWeight: "800", fontSize: 16 }}>−</Text>
                  </Pressable>
                </View>
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
  shopRow: { flexDirection: "row", alignItems: "center", paddingVertical: 4, gap: 6 },
  shopMain: { flex: 1, flexDirection: "row", alignItems: "center" },
  checkbox: {
    width: 18,
    height: 18,
    borderRadius: 4,
    borderWidth: 2,
    marginRight: 8,
  },
  minusBtn: {
    width: 32,
    height: 32,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
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
