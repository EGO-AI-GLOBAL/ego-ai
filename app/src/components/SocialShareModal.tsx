import React, { useRef, useState } from "react";
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
import type { AppColors } from "@/theme/colors";
import { STORIES_POST_TIP } from "@/constants/socialProfiles";
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

/** WhatsApp + Instagram/Stories + TikTok — mesmo fluxo da antiga Ofensiva/Desafio. */
export function SocialShareModal({
  colors,
  visible,
  onClose,
  canShare = true,
  sheetTitle = "Postar e desafiar",
  sheetSub = "Ranking visível — só mostra seus dias. O detalhe fica privado no app.",
  card,
  buildShareText,
  shareTitle,
  onWhatsApp,
  onTikTok,
}: SocialShareModalProps) {
  const [busy, setBusy] = useState(false);
  const cardRef = useRef<View>(null);

  if (!canShare) return null;

  const onStories = async () => {
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
      Alert.alert("Dica para o Story", STORIES_POST_TIP);
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
          {onTikTok ? (
            <Pressable
              onPress={() => void onTk()}
              disabled={busy}
              style={[styles.btn, { backgroundColor: colors.text, opacity: busy ? 0.7 : 1 }]}
            >
              <Text style={styles.btnText}>Partilhar no TikTok</Text>
            </Pressable>
          ) : null}
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
  btn: { borderRadius: 12, paddingVertical: 14, alignItems: "center" },
  btnText: { color: "#fff", fontWeight: "800", fontSize: 15 },
  close: { alignItems: "center", paddingVertical: 8 },
});
