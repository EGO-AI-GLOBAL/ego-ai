import * as Haptics from "expo-haptics";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { saveDailyCarePetName } from "@/api/client";
import type { DailyCareInfo } from "@/api/types";

type Props = {
  visible: boolean;
  /** Nome actual (para editar em vez de baptizar). */
  currentName?: string | null;
  onClose: () => void;
  onSaved: (care: DailyCareInfo) => void;
};

const NAME_MAX = 20;

function sanitizePetName(raw: string): string {
  const cleaned = Array.from(raw || "")
    .filter((ch) => /[\p{L}\p{N}\s'.-]/u.test(ch))
    .join("");
  return cleaned.replace(/\s+/g, " ").trim().slice(0, NAME_MAX);
}

/** Baptizar o monstrinho — o vínculo começa quando ele deixa de ser "o monstrinho". */
export function MoodPetNameModal({ visible, currentName, onClose, onSaved }: Props) {
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (visible) {
      setDraft(sanitizePetName(currentName || ""));
      setError(null);
    }
  }, [visible, currentName]);

  const isRename = Boolean((currentName || "").trim());
  const clean = sanitizePetName(draft);

  const onSave = async () => {
    if (!clean || saving) return;
    setSaving(true);
    setError(null);
    try {
      const res = await saveDailyCarePetName(clean);
      if (!res?.daily_care) {
        setError("Não foi possível guardar. Tenta outra vez.");
        return;
      }
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      onSaved(res.daily_care);
      onClose();
    } catch {
      setError("Não foi possível guardar. Tenta outra vez.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={() => {}}>
          <Text style={styles.emoji}>💜</Text>
          <Text style={styles.title}>
            {isRename ? "Mudar o nome do monstrinho" : "Como se chama o seu monstrinho?"}
          </Text>
          <Text style={styles.hint}>
            {isRename
              ? "Pode mudar sempre que quiser."
              : "Ele fica com esse nome no seu jardim, todos os dias."}
          </Text>

          <TextInput
            style={styles.input}
            value={draft}
            onChangeText={setDraft}
            placeholder="Ex.: Tico, Nuvem, Pipoca…"
            placeholderTextColor="#9CA3AF"
            maxLength={NAME_MAX}
            autoFocus
            returnKeyType="done"
            onSubmitEditing={() => void onSave()}
          />
          {error ? <Text style={styles.error}>{error}</Text> : null}

          <View style={styles.actions}>
            <Pressable onPress={onClose} style={styles.cancelBtn}>
              <Text style={styles.cancelText}>Agora não</Text>
            </Pressable>
            <Pressable
              onPress={() => void onSave()}
              disabled={saving || !clean}
              style={[styles.saveBtn, saving || !clean ? styles.saveBtnDisabled : null]}
            >
              {saving ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <Text style={styles.saveText}>{isRename ? "Guardar" : "É esse!"}</Text>
              )}
            </Pressable>
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.45)",
    justifyContent: "center",
    padding: 24,
  },
  sheet: {
    backgroundColor: "#fff",
    borderRadius: 18,
    padding: 20,
  },
  emoji: { fontSize: 30, textAlign: "center" },
  title: {
    fontSize: 18,
    fontWeight: "900",
    color: "#111",
    textAlign: "center",
    marginTop: 6,
  },
  hint: {
    fontSize: 13,
    color: "#666",
    marginTop: 8,
    lineHeight: 18,
    textAlign: "center",
  },
  input: {
    marginTop: 16,
    borderWidth: 1,
    borderColor: "#E5E7EB",
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    color: "#111",
  },
  error: { color: "#DC2626", fontSize: 12, marginTop: 8 },
  actions: { flexDirection: "row", gap: 10, marginTop: 16 },
  cancelBtn: {
    flex: 1,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#E5E7EB",
  },
  cancelText: { fontWeight: "700", color: "#444" },
  saveBtn: {
    flex: 1,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
    backgroundColor: "#7B2CBF",
  },
  saveBtnDisabled: { opacity: 0.5 },
  saveText: { color: "#fff", fontWeight: "800" },
});
