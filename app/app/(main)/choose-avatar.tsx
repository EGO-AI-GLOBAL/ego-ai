import { router } from "expo-router";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { PersonaPicker } from "@/components/PersonaPicker";
import { DEFAULT_PERSONA } from "@/constants/personas";
import type { PersonaChoice } from "@/constants/personas";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/hooks/useDashboard";
import {
  getLocalPersonaChoice,
  markPersonaConfiguredLocal,
  saveLocalPersonaChoice,
} from "@/storage/personaPrefs";
import { useColors } from "@/theme/ThemeContext";
import { resolveUserId } from "@/utils/resolveUserId";

export default function ChooseAvatarScreen() {
  const colors = useColors();
  const { session } = useAuth();
  const { data, setPersona } = useDashboard();
  const [persona, setPersonaLocal] = useState<PersonaChoice>(DEFAULT_PERSONA);
  const [checking, setChecking] = useState(true);
  const completingRef = useRef(false);
  const savedChoiceRef = useRef<PersonaChoice>(DEFAULT_PERSONA);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const uid = resolveUserId(session, data.me?.user_id);
      if (!uid) {
        if (!cancelled) setChecking(false);
        return;
      }
      const local = await getLocalPersonaChoice(uid);
      if (local?.avatar_id && local?.voice_id) {
        if (!cancelled) setPersonaLocal(local);
        if (!cancelled) router.replace("/(main)/chat");
        return;
      }
      if (!cancelled) setChecking(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [session, data.me?.user_id]);

  const onComplete = useCallback(async () => {
    if (completingRef.current) return;
    completingRef.current = true;
    const choice = savedChoiceRef.current;
    const uid = resolveUserId(session, data.me?.user_id);
    await setPersona(choice.avatar_id, choice.voice_id);
    if (uid) {
      await markPersonaConfiguredLocal(uid);
      await saveLocalPersonaChoice(uid, choice);
    }
    router.replace("/(main)/chat");
  }, [setPersona, session, data.me?.user_id]);

  if (checking) {
    return (
      <View style={[styles.fill, styles.centered, { backgroundColor: colors.bg }]}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <SafeAreaView style={[styles.fill, { backgroundColor: colors.bg }]}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={[styles.title, { color: colors.text }]}>
          Escolha o seu assistente
        </Text>
        <Text style={[styles.sub, { color: colors.textMuted }]}>
          Pode trocar depois em Conta. O avatar anima a boca quando a IA fala.
        </Text>

        <PersonaPicker
          colors={colors}
          variant="onboarding"
          planTier={data.access?.plan_tier || "essential"}
          persona={persona}
          onPersonaChange={setPersonaLocal}
          onSaved={async (choice) => {
            savedChoiceRef.current = choice;
            await setPersona(choice.avatar_id, choice.voice_id);
          }}
          onComplete={onComplete}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  centered: { justifyContent: "center", alignItems: "center" },
  scroll: {
    flexGrow: 1,
    justifyContent: "center",
    paddingHorizontal: 24,
    paddingVertical: 32,
  },
  title: {
    fontSize: 28,
    fontWeight: "800",
    textAlign: "center",
    letterSpacing: -0.5,
  },
  sub: {
    fontSize: 15,
    lineHeight: 22,
    textAlign: "center",
    marginTop: 10,
    marginBottom: 28,
  },
});
