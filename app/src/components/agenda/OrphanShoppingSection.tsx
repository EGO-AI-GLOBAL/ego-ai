import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  Text,
  TextInput,
  View,
} from "react-native";
import { createShoppingItem, deleteShoppingItem } from "@/api/client";
import type { ShoppingListItem } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { ShoppingItemRow } from "@/components/agenda/ShoppingItemRow";
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
    if (!id || item.done) return;
    setBusyId(id);
    try {
      await deleteShoppingItem(id);
      await onRefresh();
    } finally {
      setBusyId(null);
    }
  };

  const onRemove = (item: ShoppingListItem) => {
    const id = String(item.id || "");
    if (!id) return;
    Alert.alert("Apagar item", `Apagar «${item.title || "item"}»?`, [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Apagar",
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
      <Text style={[s.section, { color: colors.textMuted }]}>Lista de compras</Text>
      {items.length === 0 ? (
        <Text style={{ color: colors.textMuted, fontSize: 13, marginBottom: 8 }}>
          Itens ficam aqui até você marcar como comprado — não somem com o dia.
        </Text>
      ) : null}
      {items.map((item) => {
        const id = String(item.id || "");
        return (
          <ShoppingItemRow
            key={id}
            colors={colors}
            title={item.title || "Item"}
            done={!!item.done}
            busy={busyId === id}
            onToggle={() => onToggle(item)}
            onApagar={() => onRemove(item)}
          />
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
