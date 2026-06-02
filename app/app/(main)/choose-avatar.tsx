import { router } from "expo-router";
import React, { useCallback, useRef, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { PersonaPicker } from "@/components/PersonaPicker";
import { DEFAULT_PERSONA } from "@/constants/personas";
import type { PersonaChoice } from "@/constants/personas";
import { useDashboard } from "@/hooks/useDashboard";
import { markPersonaConfiguredLocal } from "@/storage/personaPrefs";
import { useColors } from "@/theme/ThemeContext";
import { useAuth } from "@/context/AuthContext";

export default function ChooseAvatarScreen() {
  const colors = useColors();
  const { session } = useAuth();
  const { refresh, setPersona } = useDashboard();
  const [persona, setPersonaLocal] = useState<PersonaChoice>(DEFAULT_PERSONA);
  const completingRef = useRef(false);
  const savedChoiceRef = useRef<PersonaChoice>(DEFAULT_PERSONA);

  const onComplete = useCallback(async () => {
    if (completingRef.current) return;
    completingRef.current = true;
    const choice = savedChoiceRef.current;
    setPersona(choice.avatar_id, choice.voice_id);
    const uid = session?.user?.id?.trim();
    if (uid) void markPersonaConfiguredLocal(uid);
    router.replace("/(main)/chat");
    try {
      await refresh();
    } catch {
      /* mantém escolha local e segue para o chat */
    } finally {
      setPersona(choice.avatar_id, choice.voice_id);
    }
  }, [refresh, setPersona, session?.user?.id]);

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
          persona={persona}
          onPersonaChange={setPersonaLocal}
          onSaved={(choice) => {
            savedChoiceRef.current = choice;
            setPersona(choice.avatar_id, choice.voice_id);
          }}
          onComplete={onComplete}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
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
