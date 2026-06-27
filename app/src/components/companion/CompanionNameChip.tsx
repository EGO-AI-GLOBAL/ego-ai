import React, { useState } from "react";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import type { WellnessJourney } from "@/api/types";
import {
  companionNeedsNameSetup,
  resolveCompanionDisplayName,
  saveCompanionName,
  sanitizeCompanionName,
} from "@/utils/egoDeBolsoCompanionName";

type Props = {
  journey: WellnessJourney;
  onSaved: (name: string) => void;
  /** Estilo claro sobre fundo escuro do bolso. */
  variant?: "pocket" | "card";
};

export function CompanionNameChip({ journey, onSaved, variant = "pocket" }: Props) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const display = resolveCompanionDisplayName(journey);
  const needsSetup = companionNeedsNameSetup(journey);
  const isPocket = variant === "pocket";

  const openEditor = () => {
    setDraft(sanitizeCompanionName(journey.companion_name ?? "") || "");
    setError(null);
    setOpen(true);
  };

  const onSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const name = await saveCompanionName(draft);
      onSaved(name);
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível guardar");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Pressable
        onPress={openEditor}
        style={[styles.chip, isPocket ? styles.chipPocket : styles.chipCard]}
        accessibilityRole="button"
        accessibilityLabel={needsSetup ? "Dar nome ao bolso" : `Editar nome ${display}`}
      >
        <Text style={[styles.chipText, isPocket ? styles.chipTextPocket : styles.chipTextCard]}>
          {needsSetup ? "Dar nome ao bolso ✨" : `${display} ✏️`}
        </Text>
      </Pressable>

      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <Pressable style={styles.sheet} onPress={() => {}}>
            <Text style={styles.sheetTitle}>Nome do seu bolso</Text>
            <Text style={styles.sheetHint}>
              Aparece nas missões, no chat e no lembrete das 18h.
            </Text>
            <TextInput
              style={styles.input}
              value={draft}
              onChangeText={setDraft}
              placeholder="Ex.: Luna, Pixel, Zuzu…"
              placeholderTextColor="#9CA3AF"
              maxLength={20}
              autoFocus
              returnKeyType="done"
              onSubmitEditing={() => void onSave()}
            />
            {error ? <Text style={styles.error}>{error}</Text> : null}
            <View style={styles.actions}>
              <Pressable onPress={() => setOpen(false)} style={styles.cancelBtn}>
                <Text style={styles.cancelText}>Cancelar</Text>
              </Pressable>
              <Pressable
                onPress={() => void onSave()}
                disabled={saving || !sanitizeCompanionName(draft)}
                style={[styles.saveBtn, saving ? styles.saveBtnDisabled : null]}
              >
                {saving ? (
                  <ActivityIndicator color="#fff" size="small" />
                ) : (
                  <Text style={styles.saveText}>Guardar</Text>
                )}
              </Pressable>
            </View>
          </Pressable>
        </Pressable>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  chip: {
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 5,
    marginBottom: 6,
    borderWidth: 1,
  },
  chipPocket: {
    backgroundColor: "rgba(255,255,255,0.12)",
    borderColor: "rgba(255,255,255,0.25)",
  },
  chipCard: {
    backgroundColor: "rgba(123,44,191,0.08)",
    borderColor: "rgba(123,44,191,0.25)",
    alignSelf: "flex-start",
    marginBottom: 8,
  },
  chipText: { fontSize: 12, fontWeight: "800" },
  chipTextPocket: { color: "#fff" },
  chipTextCard: { color: "#7B2CBF" },
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.45)",
    justifyContent: "center",
    padding: 24,
  },
  sheet: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 18,
  },
  sheetTitle: { fontSize: 18, fontWeight: "900", color: "#111" },
  sheetHint: { fontSize: 13, color: "#666", marginTop: 6, lineHeight: 18 },
  input: {
    marginTop: 14,
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
  saveBtnDisabled: { opacity: 0.6 },
  saveText: { color: "#fff", fontWeight: "800" },
});
