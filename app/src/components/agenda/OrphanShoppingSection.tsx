import React, { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  Text,
  TextInput,
  View,
} from "react-native";
import { createShoppingItem, patchShoppingItem } from "@/api/client";
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
  const [toggling, setToggling] = useState<string | null>(null);

  if (!items.length && !title) {
    /* still show section header when empty — user can add */
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
    setToggling(id);
    try {
      await patchShoppingItem(id, { done: true });
      await onRefresh();
    } finally {
      setToggling(null);
    }
  };

  return (
    <>
      <Text style={[s.section, { color: colors.textMuted }]}>Comprar quando puder</Text>
      {items.length === 0 ? (
        <Text style={[s.muted, { color: colors.textMuted, marginBottom: 8 }]}>
          Itens avulsos do descarrego aparecem aqui (remédio, mercado, etc.).
        </Text>
      ) : (
        items.map((item) => {
          const id = String(item.id || "");
          return (
            <Pressable
              key={id}
              onPress={() => onToggle(item)}
              disabled={toggling === id}
              style={({ pressed }) => [
                {
                  flexDirection: "row",
                  alignItems: "center",
                  paddingVertical: 8,
                  opacity: pressed || toggling === id ? 0.7 : 1,
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
                  marginRight: 10,
                }}
              />
              <Text style={{ color: colors.text, flex: 1, fontSize: 15 }}>
                {item.title || "Item"}
              </Text>
              {toggling === id ? <ActivityIndicator size="small" color={colors.primary} /> : null}
            </Pressable>
          );
        })
      )}
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
