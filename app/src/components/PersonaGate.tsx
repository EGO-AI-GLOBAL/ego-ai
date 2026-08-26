import { Redirect, useSegments } from "expo-router";
import React, { useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/hooks/useDashboard";
import { getLocalPersonaChoice } from "@/storage/personaPrefs";
import { useColors } from "@/theme/ThemeContext";
import { resolveUserId } from "@/utils/resolveUserId";

type Props = {
  children: React.ReactNode;
};

export function PersonaGate({ children }: Props) {
  const colors = useColors();
  const { session } = useAuth();
  const { data, loading, personaGateOk } = useDashboard();
  const segments = useSegments();
  const onChooseAvatar = segments.includes("choose-avatar");
  const [localReady, setLocalReady] = useState(false);
  const [hasLocalChoice, setHasLocalChoice] = useState(false);
  const uid = resolveUserId(session, data.me?.user_id);

  useEffect(() => {
    if (!uid) {
      setHasLocalChoice(false);
      setLocalReady(true);
      return;
    }
    let cancelled = false;
    void getLocalPersonaChoice(uid).then((choice) => {
      if (cancelled) return;
      setHasLocalChoice(Boolean(choice?.avatar_id && choice?.voice_id));
      setLocalReady(true);
    });
    return () => {
      cancelled = true;
    };
  }, [uid]);

  useEffect(() => {
    if (personaGateOk) setHasLocalChoice(true);
  }, [personaGateOk]);

  const personaReady = hasLocalChoice || personaGateOk;
  const hasCachedShell = Boolean(data.daily_care?.question || data.me?.user_id);
  const bootstrapping = !personaReady && !hasCachedShell && !localReady;

  if (bootstrapping) {
    return (
      <View
        style={{
          flex: 1,
          justifyContent: "center",
          alignItems: "center",
          backgroundColor: colors.bg,
        }}
      >
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (!personaReady && !onChooseAvatar) {
    return <Redirect href="/(main)/choose-avatar" />;
  }

  return <>{children}</>;
}
