import React, { useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Modal,
  Pressable,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  View,
} from "react-native";
import type { AppColors } from "@/theme/colors";
import {
  INSTAGRAM_POST_TIP,
  INSTAGRAM_REELS_TIP,
  STORIES_POST_TIP,
} from "@/constants/socialProfiles";
import { SocialFollowBar } from "./SocialFollowBar";

export type SocialShareModalProps = {
  colors: AppColors;
  visible: boolean;
  onClose: () => void;
  canShare?: boolean;
  sheetTitle?: string;
  sheetSub?: string;
  card: React.ReactNode;
  buildShareText: () => string;
  shareTitle: string;
  onWhatsApp: (text: string) => Promise<void>;
  onTikTok?: (text: string) => Promise<void>;
};

/** WhatsApp + Instagram (Stories / Post / Reels) + TikTok. */
export function SocialShareModal({
  colors,
  visible,
  onClose,
  canShare = true,
  sheetTitle = "Postar e desafiar",
  sheetSub = "Escolha onde publicar — links Android e iPhone na legenda.",
  card,
  buildShareText,
  shareTitle,
  onWhatsApp,
  onTikTok,
}: SocialShareModalProps) {
  const [busy, setBusy] = useState(false);
  const cardRef = useRef<View>(null);

  if (!canShare) return null;

  const shareImage = async (tip: string) => {
    setBusy(true);
    try {
      const message = buildShareText();
      try {
        const { captureRef } = await import("react-native-view-shot");
        const uri = await captureRef(cardRef, { format: "png", quality: 1 });
        await Share.share({ url: uri, message });
      } catch {
        await Share.share({ message, title: shareTitle });
      }
      Alert.alert("Dica", tip);
    } finally {
      setBusy(false);
    }
  };

  const onWa = async () => {
    setBusy(true);
    try {
      await onWhatsApp(buildShareText());
    } finally {
      setBusy(false);
    }
  };

  const onTk = async () => {
    if (!onTikTok) return;
    setBusy(true);
    try {
      await onTikTok(buildShareText());
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
          <ScrollView
            contentContainerStyle={styles.scroll}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            <Text style={[styles.sheetTitle, { color: colors.text }]}>{sheetTitle}</Text>
            <Text style={[styles.sheetSub, { color: colors.textMuted }]}>{sheetSub}</Text>
            <View ref={cardRef} collapsable={false}>
              {card}
            </View>
            <Pressable
              onPress={() => void onWa()}
              disabled={busy}
              style={[styles.btn, { backgroundColor: "#25D366", opacity: busy ? 0.7 : 1 }]}
            >
              <Text style={styles.btnText}>WhatsApp</Text>
            </Pressable>
            <Pressable
              onPress={() => void shareImage(STORIES_POST_TIP)}
              disabled={busy}
              style={[styles.btn, { backgroundColor: "#E1306C", opacity: busy ? 0.7 : 1 }]}
            >
              {busy ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.btnText}>Instagram Stories</Text>
              )}
            </Pressable>
            <Pressable
              onPress={() => void shareImage(INSTAGRAM_POST_TIP)}
              disabled={busy}
              style={[styles.btn, styles.btnOutline, { borderColor: "#E1306C", opacity: busy ? 0.7 : 1 }]}
            >
              <Text style={[styles.btnText, { color: "#E1306C" }]}>Instagram Post</Text>
            </Pressable>
            <Pressable
              onPress={() => void shareImage(INSTAGRAM_REELS_TIP)}
              disabled={busy}
              style={[styles.btn, styles.btnOutline, { borderColor: colors.text, opacity: busy ? 0.7 : 1 }]}
            >
              <Text style={[styles.btnText, { color: colors.text }]}>Instagram Reels</Text>
            </Pressable>
            {onTikTok ? (
              <Pressable
                onPress={() => void onTk()}
                disabled={busy}
                style={[styles.btn, { backgroundColor: colors.text, opacity: busy ? 0.7 : 1 }]}
              >
                <Text style={styles.btnText}>TikTok</Text>
              </Pressable>
            ) : null}
            <SocialFollowBar colors={colors} compact />
            <Pressable onPress={onClose} style={styles.close}>
              <Text style={{ color: colors.textMuted, fontWeight: "600" }}>Fechar</Text>
            </Pressable>
          </ScrollView>
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
    padding: 16,
  },
  sheet: { borderRadius: 16, borderWidth: 1, maxHeight: "92%" },
  scroll: { padding: 16, gap: 10 },
  sheetTitle: { fontSize: 18, fontWeight: "800", textAlign: "center" },
  sheetSub: { fontSize: 12, textAlign: "center", lineHeight: 17, marginBottom: 4 },
  btn: { borderRadius: 12, paddingVertical: 13, alignItems: "center" },
  btnOutline: { backgroundColor: "transparent", borderWidth: 2 },
  btnText: { color: "#fff", fontWeight: "800", fontSize: 15 },
  close: { alignItems: "center", paddingVertical: 8 },
});
