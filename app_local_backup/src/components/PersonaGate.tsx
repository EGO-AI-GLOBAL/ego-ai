import { Redirect, useSegments } from "expo-router";
import React, { useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/hooks/useDashboard";
import { isPersonaConfiguredLocal } from "@/storage/personaPrefs";
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
  const [localConfigured, setLocalConfigured] = useState(false);
  const uid = resolveUserId(session, data.me?.user_id);

  useEffect(() => {
    if (!uid) {
      setLocalConfigured(false);
      setLocalReady(true);
      return;
    }
    void isPersonaConfiguredLocal(uid).then((ok) => {
      setLocalConfigured(ok);
      setLocalReady(true);
    });
  }, [uid, personaGateOk]);

  const configured = personaGateOk || localConfigured;

  if (!localReady || (loading && !data.me && !localConfigured)) {
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

  if (!configured && !onChooseAvatar) {
    return <Redirect href="/(main)/choose-avatar" />;
  }

  return <>{children}</>;
}
