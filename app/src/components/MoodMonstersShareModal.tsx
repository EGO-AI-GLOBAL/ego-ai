import React from "react";
import { StyleSheet, Text, View } from "react-native";
import type { DailyCareInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import {
  buildMoodMonstersShareText,
  shareMoodMonstersTikTok,
  shareMoodMonstersWhatsApp,
} from "@/utils/whatsappShare";
import { socialCardFooter } from "@/constants/socialProfiles";
import { SocialShareModal } from "./SocialShareModal";

type Props = {
  colors: AppColors;
  care: DailyCareInfo;
  visible: boolean;
  onClose: () => void;
};

function CardFace({ care }: { care: DailyCareInfo }) {
  const days = care.current ?? 0;
  const emoji = care.last_mood_emoji || "💜";
  const monster = care.last_mood_label || "Monstrinho";
  const rank = care.ranking;
  const tierLine = rank ? `${rank.tier_emoji} ${rank.tier_label}` : `${days} dias`;
  return (
    <View style={styles.card}>
      <Text style={styles.brand}>EGO-AI</Text>
      <Text style={styles.title}>Monstrinhos do Humor</Text>
      <Text style={styles.tier}>{tierLine}</Text>
      <Text style={styles.monster}>{monster}</Text>
      <Text style={styles.mood}>{emoji}</Text>
      <Text style={styles.days}>{days}</Text>
      <Text style={styles.daysLabel}>{days === 1 ? "dia no jardim" : "dias no jardim"}</Text>
      <Text style={styles.cta}>Quem doma o humor hoje?</Text>
      <Text style={styles.ctaSub}>Responde com teu número de dias 💜</Text>
      {rank ? (
        <Text style={styles.topMeta}>Top comunidade: {rank.community_top_days} dias</Text>
      ) : null}
      <Text style={styles.social}>{socialCardFooter()}</Text>
    </View>
  );
}

export function MoodMonstersShareModal({ colors, care, visible, onClose }: Props) {
  return (
    <SocialShareModal
      colors={colors}
      visible={visible}
      onClose={onClose}
      canShare={care.can_share}
      sheetTitle="Postar e desafiar"
      sheetSub="Mostre seu monstrinho do dia — links Android e iPhone na legenda."
      card={<CardFace care={care} />}
      buildShareText={() => buildMoodMonstersShareText(care)}
      shareTitle="Monstrinhos do Humor EGO-AI"
      onWhatsApp={async () => {
        await shareMoodMonstersWhatsApp(care);
      }}
      onTikTok={async () => {
        await shareMoodMonstersTikTok(care);
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
    backgroundColor: "#5B4FCF",
  },
  brand: { color: "rgba(255,255,255,0.85)", fontSize: 13, fontWeight: "700", letterSpacing: 1 },
  title: { color: "#fff", fontSize: 17, fontWeight: "700", marginTop: 4 },
  tier: { color: "#FFE566", fontSize: 15, fontWeight: "800", marginTop: 6 },
  monster: { color: "#fff", fontSize: 22, fontWeight: "800", marginTop: 10 },
  mood: { fontSize: 44, marginTop: 4 },
  days: { color: "#FFE566", fontSize: 52, fontWeight: "900", lineHeight: 58, marginTop: 8 },
  daysLabel: { color: "rgba(255,255,255,0.9)", fontSize: 14, fontWeight: "600" },
  cta: { color: "#FFE566", fontSize: 16, fontWeight: "800", textAlign: "center", marginTop: 14 },
  ctaSub: { color: "#fff", fontSize: 14, fontWeight: "700", marginTop: 4 },
  topMeta: { color: "rgba(255,255,255,0.85)", fontSize: 12, fontWeight: "600", marginTop: 8 },
  social: { color: "rgba(255,255,255,0.8)", fontSize: 11, marginTop: 12, textAlign: "center" },
});
