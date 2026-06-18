import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  Text,
  TextInput,
  View,
} from "react-native";
import { createShoppingItem, deleteShoppingItem, patchShoppingItem } from "@/api/client";
import type { ShoppingListItem } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { agendaFormStyles as s } from "./agendaFormStyles";

export function OrphanShoppingSection({
  colors,
  items,
  onRefresh,
}: {
  colors: AppColors;
  items: ShoppingListItem[];
  onRefresh: () => Promise<void>;
}) {
  const [title, setTitle] = useState("");
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  if (!items.length) {
    return null;
  }

  const onAdd = async () => {
    const t = title.trim();
    if (!t) return;
    setSaving(true);
    try {
      await createShoppingItem({ title: t, category: "mercado" });
      setTitle("");
      await onRefresh();
    } finally {
      setSaving(false);
    }
  };

  const onToggle = async (item: ShoppingListItem) => {
    const id = String(item.id || "");
    if (!id) return;
    setBusyId(id);
    try {
      await patchShoppingItem(id, { done: !item.done });
      await onRefresh();
    } finally {
      setBusyId(null);
    }
  };

  const onRemove = (item: ShoppingListItem) => {
    const id = String(item.id || "");
    if (!id) return;
    Alert.alert("Remover item", `Remover «${item.title || "item"}»?`, [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Remover",
        style: "destructive",
        onPress: async () => {
          setBusyId(id);
          try {
            await deleteShoppingItem(id);
            await onRefresh();
          } finally {
            setBusyId(null);
          }
        },
      },
    ]);
  };

  return (
    <>
      <Text style={[s.section, { color: colors.textMuted }]}>Comprar quando puder</Text>
      {items.map((item) => {
        const id = String(item.id || "");
        const isDone = !!item.done;
        return (
          <View
            key={id}
            style={{ flexDirection: "row", alignItems: "center", paddingVertical: 6, gap: 6 }}
          >
            <Pressable
              onPress={() => onToggle(item)}
              disabled={busyId === id}
              style={({ pressed }) => [
                {
                  flex: 1,
                  flexDirection: "row",
                  alignItems: "center",
                  opacity: pressed || busyId === id ? 0.7 : 1,
                },
              ]}
            >
              <View
                style={{
                  width: 20,
                  height: 20,
                  borderRadius: 4,
                  borderWidth: 2,
                  borderColor: colors.primary,
                  backgroundColor: isDone ? colors.primary : "transparent",
                  marginRight: 10,
                }}
              />
              <Text
                style={{
                  color: colors.text,
                  flex: 1,
                  fontSize: 15,
                  textDecorationLine: isDone ? "line-through" : "none",
                  opacity: isDone ? 0.65 : 1,
                }}
              >
                {item.title || "Item"}
              </Text>
              {busyId === id ? <ActivityIndicator size="small" color={colors.primary} /> : null}
            </Pressable>
            <Pressable
              onPress={() => onRemove(item)}
              disabled={busyId === id}
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                borderWidth: 1,
                borderColor: colors.border,
                alignItems: "center",
                justifyContent: "center",
              }}
              accessibilityLabel="Remover item"
            >
              <Text style={{ color: colors.danger, fontWeight: "800", fontSize: 16 }}>−</Text>
            </Pressable>
          </View>
        );
      })}
      <View style={{ flexDirection: "row", gap: 8, marginTop: 8, marginBottom: 16 }}>
        <TextInput
          value={title}
          onChangeText={setTitle}
          placeholder="Adicionar item avulso"
          placeholderTextColor={colors.textMuted}
          style={[
            s.inviteInput,
            { flex: 1, color: colors.text, borderColor: colors.border, backgroundColor: colors.bg },
          ]}
        />
        <Pressable
          onPress={onAdd}
          disabled={saving || !title.trim()}
          style={[s.inviteBtn, { paddingHorizontal: 16, backgroundColor: colors.primary }]}
        >
          {saving ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={s.inviteBtnText}>+</Text>
          )}
        </Pressable>
      </View>
    </>
  );
}
