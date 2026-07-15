import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { submitDailyCareJournalNote } from "@/api/client";
import type { DailyCareInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";

const NOTE_MAX = 280;

type Props = {
  colors: AppColors;
  care: DailyCareInfo;
  onUpdate: (care: DailyCareInfo) => void;
  /** Carta guardada → reação do pet (clip distinto). */
  onLetterSaved?: () => void;
};

export function MoodJournalTodayNote({ colors, care, onUpdate, onLetterSaved }: Props) {
  const todayEntry = (care.mood_journal ?? []).find((e) => e.date === care.last_date);
  const [draft, setDraft] = useState(todayEntry?.note ?? "");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setDraft(todayEntry?.note ?? "");
    setSaved(false);
  }, [todayEntry?.note, care.last_date]);

  if (!care.checked_today) return null;

  const onSave = async () => {
    if (busy) return;
    setBusy(true);
    setSaved(false);
    try {
      const res = await submitDailyCareJournalNote(draft);
      if (!res?.daily_care) return;
      onUpdate(res.daily_care);
      setSaved(true);
      onLetterSaved?.();
    } finally {
      setBusy(false);
    }
  };

  const dirty = (draft.trim() || "") !== (todayEntry?.note?.trim() || "");

  return (
    <View style={[styles.wrap, { borderColor: colors.border, backgroundColor: colors.bgCard }]}>
      <Text style={[styles.title, { color: colors.text }]}>💌 Carta pro monstrinho</Text>
      <Text style={[styles.hint, { color: colors.textMuted }]}>
        Escreva o que pesa — só o seu monstrinho guarda. Ninguém lê. Falar no chat é opcional.
      </Text>
      <TextInput
        style={[
          styles.input,
          { color: colors.text, borderColor: colors.border, backgroundColor: colors.bg },
        ]}
        value={draft}
        onChangeText={(t) => {
          setDraft(t.slice(0, NOTE_MAX));
          setSaved(false);
        }}
        placeholder="Domingo sozinha, cabeça não para, ou só o que pesou hoje…"
        placeholderTextColor={colors.textMuted}
        multiline
        maxLength={NOTE_MAX}
        editable={!busy}
      />
      <View style={styles.footer}>
        <Text style={[styles.count, { color: colors.textMuted }]}>
          {draft.length}/{NOTE_MAX}
        </Text>
        <Pressable
          onPress={() => void onSave()}
          disabled={busy || !dirty}
          style={[
            styles.btn,
            {
              backgroundColor: dirty ? colors.primary : colors.border,
              opacity: busy ? 0.7 : 1,
            },
          ]}
        >
          {busy ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <Text style={styles.btnText}>{saved && !dirty ? "Carta guardada ✓" : "Guardar carta"}</Text>
          )}
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginBottom: 12,
    padding: 12,
    borderRadius: 14,
    borderWidth: 1,
  },
  title: { fontSize: 14, fontWeight: "800" },
  hint: { fontSize: 11, fontWeight: "600", marginTop: 2, marginBottom: 8 },
  input: {
    minHeight: 72,
    borderWidth: 1,
    borderRadius: 12,
    padding: 10,
    fontSize: 14,
    lineHeight: 20,
    textAlignVertical: "top",
  },
  footer: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 8,
  },
  count: { fontSize: 11, fontWeight: "600" },
  btn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 10,
    minWidth: 110,
    alignItems: "center",
  },
  btnText: { color: "#fff", fontSize: 13, fontWeight: "800" },
});
