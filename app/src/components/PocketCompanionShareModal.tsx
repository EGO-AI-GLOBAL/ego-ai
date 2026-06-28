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

import { CompanionSprite } from "./companion/CompanionSprite";



type Props = {

  colors: AppColors;

  journey: WellnessJourney;

  visible: boolean;

  onClose: () => void;

};



function CardFace({ journey }: { journey: WellnessJourney }) {

  const level = journey.level ?? 1;

  const max = journey.max_level ?? 500;

  const title = (journey.title || "EGO de Bolso").trim();

  const stage = journey.companion_stage ?? "egg";

  return (

    <View style={styles.card}>

      <Text style={styles.brand}>EGO-AI</Text>

      <Text style={styles.title}>EGO de Bolso</Text>

      <CompanionSprite
        stage={stage}
        size={80}
        happy={journey.level_complete}
        eggColor={journey.companion_egg_color}
      />

      <Text style={styles.level}>

        Nível {level}/{max}

      </Text>

      <Text style={styles.subtitle}>

        {journey.emoji || "🥚"} {title}

      </Text>

      <Text style={styles.cta}>Eu estou no nível {level}. E você?</Text>

      <Text style={styles.ctaSub}>Tamagotchi de bem-estar — estilo anos 90 💜</Text>

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

      sheetTitle="Postar meu EGO de Bolso"

      sheetSub="Escolha a rede — cartão + links na legenda. Desafie amigos!"

      card={<CardFace journey={journey} />}

      buildShareText={() => buildPocketCompanionShareText(journey)}

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

    paddingHorizontal: 20,

    alignItems: "center",

    backgroundColor: "#2D1B4E",

  },

  brand: { color: "rgba(255,255,255,0.85)", fontSize: 13, fontWeight: "700", letterSpacing: 1 },

  title: { color: "#fff", fontSize: 18, fontWeight: "800", marginTop: 4 },

  level: { color: "#FFE566", fontSize: 28, fontWeight: "900", marginTop: 8 },

  subtitle: { color: "rgba(255,255,255,0.92)", fontSize: 15, fontWeight: "700", marginTop: 6 },

  cta: { color: "#FFE566", fontSize: 15, fontWeight: "800", textAlign: "center", marginTop: 14 },

  ctaSub: { color: "#fff", fontSize: 13, fontWeight: "600", marginTop: 4, textAlign: "center" },

  social: { color: "rgba(255,255,255,0.8)", fontSize: 11, marginTop: 12, textAlign: "center" },

});


