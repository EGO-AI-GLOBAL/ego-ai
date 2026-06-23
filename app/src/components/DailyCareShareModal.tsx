import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Modal,
  Pressable,
  Share,
  StyleSheet,
  Text,
  View,
} from "react-native";
import type { DailyCareInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import {
  buildDailyCareShareText,
  shareDailyCareStories,
  shareDailyCareTikTok,
  shareDailyCareWhatsApp,
} from "@/utils/whatsappShare";
import { socialCardFooter, STORIES_POST_TIP } from "@/constants/socialProfiles";
import { SocialFollowBar } from "./SocialFollowBar";

type Props = {
  colors: AppColors;
  care: DailyCareInfo;
  visible: boolean;
  onClose: () => void;
};

function CardFace({ care }: { care: DailyCareInfo }) {
  const days = care.current ?? 0;
  const emoji = care.last_mood_emoji || "💜";
  const rank = care.ranking;
  const tierLine = rank
    ? `${rank.tier_emoji} ${rank.tier_label}`
    : `${days} dias`;
  return (
    <View style={styles.card}>
      <Text style={styles.brand}>EGO-AI</Text>
      <Text style={styles.title}>Desafio Diário</Text>
      <Text style={styles.tier}>{tierLine}</Text>
      <Text style={styles.days}>{days}</Text>
      <Text style={styles.daysLabel}>{days === 1 ? "dia" : "dias"} de cuidado</Text>
      <Text style={styles.mood}>{emoji}</Text>
      <Text style={styles.cta}>Quantos dias você cuida de si?</Text>
      <Text style={styles.ctaSub}>Responde com teu número 🔥</Text>
      {rank ? (
        <Text style={styles.topMeta}>Top comunidade: {rank.community_top_days} dias</Text>
      ) : null}
      <Text style={styles.social}>{socialCardFooter()}</Text>
    </View>
  );
}

export function DailyCareShareModal({ colors, care, visible, onClose }: Props) {
  const [busy, setBusy] = useState(false);
  const cardRef = React.useRef<View>(null);

  if (!care.can_share) return null;

  const onWhatsApp = async () => {
    setBusy(true);
    try {
      await shareDailyCareWhatsApp(care);
    } finally {
      setBusy(false);
    }
  };

  const onStories = async () => {
    setBusy(true);
    try {
      try {
        const { captureRef } = await import("react-native-view-shot");
        const uri = await captureRef(cardRef, { format: "png", quality: 1 });
        await shareDailyCareStories(care, uri);
      } catch {
        await Share.share({ message: buildDailyCareShareText(care) });
      }
      Alert.alert("Dica para o Story", STORIES_POST_TIP);
    } finally {
      setBusy(false);
    }
  };

  const onTikTok = async () => {
    setBusy(true);
    try {
      await shareDailyCareTikTok(care);
      Alert.alert(
        "TikTok",
        "Escolha TikTok no menu. Cole a legenda na descrição do vídeo ou story."
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={[styles.sheet, { backgroundColor: colors.bgCard, borderColor: colors.border }]}>
          <Text style={[styles.sheetTitle, { color: colors.text }]}>Postar e desafiar</Text>
          <Text style={[styles.sheetSub, { color: colors.textMuted }]}>
            Ranking visível — só mostra seus dias. O detalhe fica privado no app.
          </Text>
          <View ref={cardRef} collapsable={false}>
            <CardFace care={care} />
          </View>
          <Pressable
            onPress={() => void onWhatsApp()}
            disabled={busy}
            style={[styles.btn, { backgroundColor: "#25D366", opacity: busy ? 0.7 : 1 }]}
          >
            <Text style={styles.btnText}>WhatsApp</Text>
          </Pressable>
          <Pressable
            onPress={() => void onStories()}
            disabled={busy}
            style={[styles.btn, { backgroundColor: "#E1306C", opacity: busy ? 0.7 : 1 }]}
          >
            {busy ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.btnText}>Instagram / Stories</Text>
            )}
          </Pressable>
          <Pressable
            onPress={() => void onTikTok()}
            disabled={busy}
            style={[styles.btn, { backgroundColor: colors.text, opacity: busy ? 0.7 : 1 }]}
          >
            <Text style={styles.btnText}>Partilhar no TikTok</Text>
          </Pressable>
          <SocialFollowBar colors={colors} compact />
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
  sheet: { borderRadius: 16, borderWidth: 1, padding: 16, gap: 10 },
  sheetTitle: { fontSize: 18, fontWeight: "800", textAlign: "center" },
  sheetSub: { fontSize: 12, textAlign: "center", lineHeight: 17, marginBottom: 4 },
  card: {
    borderRadius: 20,
    paddingVertical: 26,
    paddingHorizontal: 20,
    alignItems: "center",
    backgroundColor: "#5B4FCF",
  },
  brand: { color: "rgba(255,255,255,0.85)", fontSize: 13, fontWeight: "700", letterSpacing: 1 },
  title: { color: "#fff", fontSize: 17, fontWeight: "700", marginTop: 4 },
  tier: { color: "#FFE566", fontSize: 15, fontWeight: "800", marginTop: 6 },
  days: { color: "#FFE566", fontSize: 64, fontWeight: "900", lineHeight: 70, marginTop: 4 },
  daysLabel: { color: "rgba(255,255,255,0.9)", fontSize: 15, fontWeight: "600" },
  mood: { fontSize: 40, marginTop: 10 },
  cta: { color: "#FFE566", fontSize: 16, fontWeight: "800", textAlign: "center", marginTop: 14 },
  ctaSub: { color: "#fff", fontSize: 14, fontWeight: "700", marginTop: 4 },
  topMeta: { color: "rgba(255,255,255,0.85)", fontSize: 12, fontWeight: "600", marginTop: 8 },
  social: { color: "rgba(255,255,255,0.8)", fontSize: 11, marginTop: 12, textAlign: "center" },
  btn: { borderRadius: 12, paddingVertical: 14, alignItems: "center" },
  btnText: { color: "#fff", fontWeight: "800", fontSize: 15 },
  close: { alignItems: "center", paddingVertical: 8 },
});
