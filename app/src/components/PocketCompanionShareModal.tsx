import React from "react";
import { LinearGradient } from "expo-linear-gradient";
import { StyleSheet, Text, View } from "react-native";
import type { WellnessJourney } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import {
  buildPocketCompanionInstagramCaption,
  pocketCompanionCardChallenge,
  pocketCompanionCardHeadline,
  pocketCompanionShareStats,
} from "@/utils/egoDeBolsoShare";
import {
  sharePocketCompanionTikTok,
  sharePocketCompanionWhatsApp,
} from "@/utils/whatsappShare";
import { socialCardFooter } from "@/constants/socialProfiles";
import { SocialShareModal } from "./SocialShareModal";
import { CompanionSprite } from "./companion/CompanionSprite";

type Props = {
  colors: AppColors;
  journey: WellnessJourney;
  visible: boolean;
  onClose: () => void;
};

function CardFace({ journey }: { journey: WellnessJourney }) {
  const s = pocketCompanionShareStats(journey);
  const stage = journey.companion_stage ?? "egg";

  return (
    <LinearGradient
      colors={["#12082A", "#2D1B4E", "#5B3FA8", "#7C5CE0"]}
      style={styles.card}
      start={{ x: 0.15, y: 0 }}
      end={{ x: 0.85, y: 1 }}
    >
      <Text style={styles.brand}>EGO-AI · EGO DE BOLSO</Text>
      <Text style={styles.petName}>{s.petName}</Text>
      <Text style={styles.stage}>
        {journey.companion_sprite_emoji ?? "🥚"} {s.stageLabel}
      </Text>
      <CompanionSprite
        stage={stage}
        size={88}
        happy={s.dayComplete || journey.level_complete}
        celebrate={s.dayComplete}
        eggColor={journey.companion_egg_color}
      />
      <Text style={styles.level}>
        Nível {s.level}
        <Text style={styles.levelMax}>/{s.max}</Text>
      </Text>
      <Text style={styles.headline}>{pocketCompanionCardHeadline(journey)}</Text>
      <View style={styles.statsRow}>
        <Text style={styles.statChip}>💜 {s.care}% cuidado</Text>
        {s.stars > 0 ? <Text style={styles.statChip}>⭐ {s.stars}</Text> : null}
        <Text style={styles.statChip}>
          {s.emoji} {s.title}
        </Text>
      </View>
      <Text style={styles.cta}>{pocketCompanionCardChallenge(journey)}</Text>
      <Text style={styles.ctaSub}>Tamagotchi de bem-estar — anos 90 com IA 💜</Text>
      <Text style={styles.social}>{socialCardFooter()}</Text>
    </LinearGradient>
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
      sheetTitle="Desafiar amigos"
      sheetSub="Cartão pronto para Stories, WhatsApp e Instagram — links na legenda."
      card={<CardFace journey={journey} />}
      buildShareText={() => buildPocketCompanionInstagramCaption(journey)}
      shareTitle="EGO de Bolso — EGO-AI"
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
    paddingVertical: 22,
    paddingHorizontal: 18,
    alignItems: "center",
    overflow: "hidden",
  },
  brand: {
    color: "rgba(255,255,255,0.85)",
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 0.8,
  },
  petName: {
    color: "#FFE566",
    fontSize: 22,
    fontWeight: "900",
    marginTop: 6,
    textAlign: "center",
  },
  stage: { color: "rgba(255,255,255,0.9)", fontSize: 13, fontWeight: "700", marginTop: 2 },
  level: { color: "#fff", fontSize: 34, fontWeight: "900", marginTop: 10 },
  levelMax: { fontSize: 18, fontWeight: "700", color: "rgba(255,255,255,0.65)" },
  headline: {
    color: "#A5F3FC",
    fontSize: 14,
    fontWeight: "800",
    textAlign: "center",
    marginTop: 8,
    lineHeight: 19,
    paddingHorizontal: 4,
  },
  statsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "center",
    gap: 6,
    marginTop: 10,
  },
  statChip: {
    color: "rgba(255,255,255,0.92)",
    fontSize: 10,
    fontWeight: "700",
    backgroundColor: "rgba(0,0,0,0.22)",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    overflow: "hidden",
  },
  cta: {
    color: "#FFE566",
    fontSize: 15,
    fontWeight: "800",
    textAlign: "center",
    marginTop: 14,
    lineHeight: 20,
  },
  ctaSub: {
    color: "#fff",
    fontSize: 12,
    fontWeight: "600",
    marginTop: 6,
    textAlign: "center",
    lineHeight: 17,
  },
  social: {
    color: "rgba(255,255,255,0.75)",
    fontSize: 10,
    marginTop: 12,
    textAlign: "center",
  },
});
