import { Redirect, useSegments } from "expo-router";
import React, { useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/hooks/useDashboard";
import { getLocalPersonaChoice } from "@/storage/personaPrefs";
import { useColors } from "@/theme/ThemeContext";
import { isProfilePhoneMissing } from "@/utils/profileComplete";
import { resolveUserId } from "@/utils/resolveUserId";

type Props = {
  children: React.ReactNode;
};

export function PersonaGate({ children }: Props) {
  const colors = useColors();
  const { session } = useAuth();
  const { data, loading } = useDashboard();
  const segments = useSegments();
  const onChooseAvatar = segments.includes("choose-avatar");
  const onCompleteProfile = segments.includes("complete-profile");
  const [localReady, setLocalReady] = useState(false);
  const [hasLocalChoice, setHasLocalChoice] = useState(false);
  const uid = resolveUserId(session, data.me?.user_id);

  useEffect(() => {
    if (!uid) {
      setHasLocalChoice(false);
      setLocalReady(true);
      return;
    }
    void getLocalPersonaChoice(uid).then((choice) => {
      setHasLocalChoice(Boolean(choice?.avatar_id && choice?.voice_id));
      setLocalReady(true);
    });
  }, [uid]);

  if (!localReady || loading) {
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

  if (
    !hasLocalChoice &&
    !onChooseAvatar &&
    !onCompleteProfile &&
    !isProfilePhoneMissing(data.me)
  ) {
    return <Redirect href="/(main)/choose-avatar" />;
  }

  return <>{children}</>;
}
