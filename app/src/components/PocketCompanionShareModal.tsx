import React from "react";
import { StyleSheet, Text, View } from "react-native";
import type { WellnessJourney } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import {
  buildPocketCompanionShareText,
  sharePocketCompanionTikTok,
  sharePocketCompanionWhatsApp,
} from "@/utils/whatsappShare";
import { socialCardFooter } from "@/constants/socialProfiles";
import { SocialShareModal } from "./SocialShareModal";

type Props = {
  colors: AppColors;
  journey: WellnessJourney;
  visible: boolean;
  onClose: () => void;
};

function CardFace({ journey }: { journey: WellnessJourney }) {
  const level = journey.level ?? 1;
  const max = journey.max_level ?? 500;
  const emoji = journey.emoji || "🥚";
  const title = (journey.title || "Companheiro").trim();
  return (
    <View style={styles.card}>
      <Text style={styles.brand}>EGO-AI</Text>
      <Text style={styles.title}>Companheiro de Bolso</Text>
      <Text style={styles.emoji}>{emoji}</Text>
      <Text style={styles.level}>
        Nível {level}/{max}
      </Text>
      <Text style={styles.subtitle}>{title}</Text>
      <Text style={styles.cta}>Lembra o bichinho dos anos 90?</Text>
      <Text style={styles.ctaSub}>Agora no bolso — com a Luna 💜</Text>
      <Text style={styles.social}>{socialCardFooter()}</Text>
    </View>
  );
}

export function PocketCompanionShareModal({ colors, journey, visible, onClose }: Props) {
  const canShare = (journey.level ?? 0) >= 1;
  return (
    <SocialShareModal
      colors={colors}
      visible={visible}
      onClose={onClose}
      canShare={canShare}
      sheetTitle="Postar e desafiar"
      sheetSub="Mostre o nível do seu companheiro — links na legenda."
      card={<CardFace journey={journey} />}
      buildShareText={() => buildPocketCompanionShareText(journey)}
      shareTitle="Companheiro de Bolso EGO-AI"
      onWhatsApp={async () => {
        await sharePocketCompanionWhatsApp(journey);
      }}
      onTikTok={async () => {
        await sharePocketCompanionTikTok(journey);
      }}
    />
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 20,
    paddingVertical: 26,
    paddingHorizontal: 20,
    alignItems: "center",
    backgroundColor: "#2D1B4E",
  },
  brand: { color: "rgba(255,255,255,0.85)", fontSize: 13, fontWeight: "700", letterSpacing: 1 },
  title: { color: "#fff", fontSize: 17, fontWeight: "700", marginTop: 4 },
  emoji: { fontSize: 56, marginTop: 10 },
  level: { color: "#FFE566", fontSize: 28, fontWeight: "900", marginTop: 8 },
  subtitle: { color: "rgba(255,255,255,0.92)", fontSize: 15, fontWeight: "700", marginTop: 6 },
  cta: { color: "#FFE566", fontSize: 15, fontWeight: "800", textAlign: "center", marginTop: 16 },
  ctaSub: { color: "#fff", fontSize: 14, fontWeight: "600", marginTop: 4 },
  social: { color: "rgba(255,255,255,0.8)", fontSize: 11, marginTop: 12, textAlign: "center" },
});
