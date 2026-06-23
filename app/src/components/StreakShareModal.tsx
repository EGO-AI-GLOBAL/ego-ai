import React, { useRef, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import type { StreakInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { streakShareHeadline } from "@/utils/streakReactions";
import { shareStreakWhatsApp, shareStreakStories } from "@/utils/whatsappShare";

type Props = {
  colors: AppColors;
  streak?: StreakInfo;
  assistantName: string;
  visible: boolean;
  onClose: () => void;
};

function StreakCardFace({
  colors,
  current,
  atRisk,
  assistantName,
}: {
  colors: AppColors;
  current: number;
  atRisk: boolean;
  assistantName: string;
}) {
  return (
    <View style={[styles.card, { backgroundColor: colors.primary }]}>
      <Text style={styles.brand}>EGO-AI</Text>
      <Text style={styles.assistant}>{assistantName}</Text>
      <Text style={styles.flame}>🔥</Text>
      <Text style={styles.days}>{current}</Text>
      <Text style={styles.headline}>{streakShareHeadline(current, atRisk)}</Text>
      <Text style={styles.tagline}>
        {atRisk ? "1 áudio salva hoje" : `Eu: ${current} dias`}
      </Text>
      <Text style={styles.cta}>Quantos você aguenta?</Text>
      <Text style={styles.ctaSub}>Responde com teu número 🔥</Text>
      <Text style={styles.footer}>EGO-AI · grátis · bem-estar</Text>
    </View>
  );
}

export function StreakShareModal({
  colors,
  streak,
  assistantName,
  visible,
  onClose,
}: Props) {
  const [busy, setBusy] = useState(false);
  const current = streak?.current ?? 0;
  const atRisk = !!(streak?.at_risk && !streak?.active_today);
  const cardRef = useRef<View>(null);

  const onShareNative = async () => {
    if (current < 1) return;
    setBusy(true);
    try {
      try {
        const { captureRef } = await import("react-native-view-shot");
        const uri = await captureRef(cardRef, { format: "png", quality: 1 });
        await shareStreakStories({
          days: current,
          atRisk,
          assistantName,
          imageUri: uri,
        });
      } catch {
        await shareStreakStories({ days: current, atRisk, assistantName });
      }
    } catch {
      /* cancelado */
    } finally {
      setBusy(false);
    }
  };

  const onShareWhatsApp = async () => {
    if (current < 1) return;
    setBusy(true);
    try {
      await shareStreakWhatsApp({ days: current, atRisk, assistantName });
    } finally {
      setBusy(false);
    }
  };

  if (current < 1) return null;

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={[styles.sheet, { backgroundColor: colors.bgCard, borderColor: colors.border }]}>
          <Text style={[styles.title, { color: colors.text }]}>Desafio entre amigos</Text>
          <View ref={cardRef} collapsable={false}>
            <StreakCardFace
              colors={colors}
              current={current}
              atRisk={atRisk}
              assistantName={assistantName}
            />
          </View>
          <Pressable
            onPress={() => void onShareWhatsApp()}
            disabled={busy}
            style={[styles.btn, { backgroundColor: "#25D366", opacity: busy ? 0.7 : 1 }]}
          >
            {busy ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.btnText}>WhatsApp</Text>
            )}
          </Pressable>
          <Pressable
            onPress={() => void onShareNative()}
            disabled={busy}
            style={[styles.btn, { backgroundColor: colors.primary, opacity: busy ? 0.7 : 1 }]}
          >
            <Text style={styles.btnText}>Instagram / Stories</Text>
          </Pressable>
          <Pressable onPress={onClose} style={styles.close}>
            <Text style={{ color: colors.textMuted, fontWeight: "600" }}>Fechar</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.55)",
    justifyContent: "center",
    padding: 20,
  },
  sheet: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 16,
    gap: 12,
  },
  title: { fontSize: 18, fontWeight: "800", textAlign: "center", marginBottom: 4 },
  card: {
    borderRadius: 20,
    paddingVertical: 28,
    paddingHorizontal: 20,
    alignItems: "center",
  },
  brand: { color: "rgba(255,255,255,0.85)", fontSize: 14, fontWeight: "700", letterSpacing: 1 },
  assistant: { color: "#fff", fontSize: 16, fontWeight: "600", marginTop: 4 },
  flame: { fontSize: 36, marginTop: 12 },
  days: { color: "#FFE566", fontSize: 72, fontWeight: "900", lineHeight: 78 },
  headline: { color: "#fff", fontSize: 22, fontWeight: "800", textAlign: "center", marginTop: 4 },
  tagline: {
    color: "rgba(255,255,255,0.9)",
    fontSize: 14,
    textAlign: "center",
    marginTop: 8,
    lineHeight: 20,
  },
  cta: {
    color: "#FFE566",
    fontSize: 18,
    fontWeight: "800",
    textAlign: "center",
    marginTop: 14,
  },
  ctaSub: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "700",
    textAlign: "center",
    marginTop: 4,
  },
  footer: { color: "rgba(255,255,255,0.75)", fontSize: 12, marginTop: 14 },
  btn: { borderRadius: 12, paddingVertical: 14, alignItems: "center" },
  btnText: { color: "#fff", fontWeight: "800", fontSize: 15 },
  close: { alignItems: "center", paddingVertical: 8 },
});
