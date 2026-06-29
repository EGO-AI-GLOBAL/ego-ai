import { router } from "expo-router";

import React, { useState } from "react";

import { Pressable, StyleSheet, Text, View, type DimensionValue } from "react-native";

import type { WellnessJourney } from "@/api/types";

import type { AppColors } from "@/theme/colors";

import { resolveEgoDeBolsoCareRoute } from "@/utils/egoDeBolsoCareRoute";

import { egoDeBolsoDailyCarePercent } from "@/utils/egoDeBolsoDailyCare";

import {

  egoDeBolsoDayCompleteMessage,

  egoDeBolsoMissionsComplete,

} from "@/utils/egoDeBolsoCompanionMood";

import { resolveCompanionDisplayName } from "@/utils/egoDeBolsoCompanionName";

import { formatWellnessPendingLine } from "@/utils/egoDeBolsoStepHints";

import { CompanionSprite } from "./companion/CompanionSprite";

import { PocketCompanionShareModal } from "./PocketCompanionShareModal";



type Props = {

  colors: AppColors;

  journey?: WellnessJourney;

  onCareHint?: (message: string) => void;

};



/** Mini-card EGO de Bolso no chat — missão do dia + postar. */

export function EgoDeBolsoChatCard({ colors, journey, onCareHint }: Props) {

  const [shareOpen, setShareOpen] = useState(false);



  if (!journey) return null;



  const dayComplete = egoDeBolsoMissionsComplete(journey);

  const care = egoDeBolsoDailyCarePercent(journey);

  const fillWidth = `${Math.max(care, care > 0 ? 8 : 0)}%` as DimensionValue;

  const stage = journey.companion_stage ?? "egg";

  const petName = resolveCompanionDisplayName(journey);

  const missionsToday = journey.missions_today ?? 0;

  const missionsPerDay = journey.missions_per_day ?? 5;

  const hasPendingMissions = !dayComplete && missionsToday < missionsPerDay;

  const pendingSteps = journey.steps?.filter((s) => !s.done) ?? [];

  const pendingLine = formatWellnessPendingLine(pendingSteps);



  const onCare = () => {

    const route = resolveEgoDeBolsoCareRoute(journey);

    if (route === "/(main)/chat") {

      onCareHint?.(`Missão de hoje: ${journey.today_task}`);

      return;

    }

    router.push(route);

  };



  const onTalk = () => {

    onCareHint?.(

      `Quero falar sobre a missão do ${petName} (${missionsToday}/${missionsPerDay} hoje): ${journey.today_task}`

    );

  };



  return (

    <>

      <View style={[styles.wrap, { backgroundColor: colors.bgCard, borderColor: colors.primary }]}>

        <Pressable onPress={() => router.push("/(main)/wellness-journey")} style={styles.row}>

          <CompanionSprite

            stage={stage}

            size={52}

            happy={dayComplete || journey.level_complete}

            eggColor={journey.companion_egg_color}

          />

          <View style={styles.body}>

            <Text style={[styles.badge, { color: colors.primary }]}>

              {petName.toUpperCase()} · EGO DE BOLSO 🥚

            </Text>

            <Text style={[styles.level, { color: colors.text }]} numberOfLines={1}>

              Nível {journey.level}/{journey.max_level} · {journey.title}

              {journey.missions_per_day && !dayComplete

                ? ` · ${missionsToday}/${missionsPerDay}`

                : ""}

            </Text>

            <View style={[styles.track, { backgroundColor: colors.border }]}>

              <View

                style={[styles.fill, { backgroundColor: colors.primary, width: fillWidth }]}

              />

            </View>

            <Text

              style={[

                styles.task,

                { color: dayComplete ? colors.primary : colors.textMuted },

              ]}

              numberOfLines={3}

            >

              {dayComplete ? egoDeBolsoDayCompleteMessage(journey) : `Hoje: ${journey.today_task}`}

            </Text>

            {hasPendingMissions && pendingLine ? (

              <Text style={[styles.pending, { color: colors.textMuted }]} numberOfLines={2}>

                Falta: {pendingLine}

              </Text>

            ) : null}

            {journey.weekly_challenge && !journey.weekly_challenge.complete ? (

              <Text style={[styles.pending, { color: colors.textMuted }]} numberOfLines={1}>

                Semana: {journey.weekly_challenge.days_done}/{journey.weekly_challenge.days_goal} dias 5/5

              </Text>

            ) : null}

          </View>

        </Pressable>

        <View style={styles.actions}>

          {hasPendingMissions ? (

            <Pressable onPress={onCare} style={[styles.btn, { backgroundColor: colors.primary }]}>

              <Text style={styles.btnText}>Cuidar agora</Text>

            </Pressable>

          ) : null}

          {hasPendingMissions && onCareHint ? (

            <Pressable

              onPress={onTalk}

              style={[styles.btnOutline, { borderColor: colors.primary }]}

            >

              <Text style={[styles.btnOutlineText, { color: colors.primary }]}>Falar disso</Text>

            </Pressable>

          ) : null}

          <Pressable

            onPress={() => setShareOpen(true)}

            style={[styles.btnOutline, { borderColor: colors.primary, flex: hasPendingMissions ? 1 : undefined }]}

          >

            <Text style={[styles.btnOutlineText, { color: colors.primary }]}>Postar</Text>

          </Pressable>

        </View>

      </View>



      <PocketCompanionShareModal

        colors={colors}

        journey={journey}

        visible={shareOpen}

        onClose={() => setShareOpen(false)}

      />

    </>

  );

}



const styles = StyleSheet.create({

  wrap: {

    borderRadius: 14,

    borderWidth: 1.5,

    padding: 12,

    marginBottom: 12,

  },

  row: { flexDirection: "row", alignItems: "center", gap: 10 },

  body: { flex: 1 },

  badge: { fontSize: 10, fontWeight: "900", letterSpacing: 0.4 },

  level: { fontSize: 13, fontWeight: "800", marginTop: 2 },

  track: {

    height: 5,

    borderRadius: 3,

    overflow: "hidden",

    marginTop: 6,

    marginBottom: 4,

  },

  fill: { height: "100%", borderRadius: 3 },

  task: { fontSize: 11, lineHeight: 15 },

  pending: { fontSize: 10, lineHeight: 14, marginTop: 4, fontStyle: "italic" },

  actions: { flexDirection: "row", gap: 8, marginTop: 10 },

  btn: {

    flex: 1,

    borderRadius: 10,

    paddingVertical: 10,

    alignItems: "center",

  },

  btnText: { color: "#fff", fontWeight: "800", fontSize: 13 },

  btnOutline: {

    flex: 1,

    borderRadius: 10,

    paddingVertical: 10,

    alignItems: "center",

    borderWidth: 1.5,

  },

  btnOutlineText: { fontWeight: "800", fontSize: 13 },

});

