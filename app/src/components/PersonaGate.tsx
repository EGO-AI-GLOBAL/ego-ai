import { Redirect, useSegments } from "expo-router";
import React, { useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/hooks/useDashboard";
import { getLocalPersonaChoice } from "@/storage/personaPrefs";
import { getLocalProfilePhone } from "@/storage/profilePhoneLocal";
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
  const [localPhone, setLocalPhone] = useState<string | null>(null);
  const uid = resolveUserId(session, data.me?.user_id);

  useEffect(() => {
    if (!uid) {
      setHasLocalChoice(false);
      setLocalPhone(null);
      setLocalReady(true);
      return;
    }
    let cancelled = false;
    void Promise.all([getLocalPersonaChoice(uid), getLocalProfilePhone(uid)]).then(
      ([choice, phone]) => {
        if (cancelled) return;
        setHasLocalChoice(Boolean(choice?.avatar_id && choice?.voice_id));
        setLocalPhone(phone);
        setLocalReady(true);
      }
    );
    return () => {
      cancelled = true;
    };
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
    !isProfilePhoneMissing(data.me, localPhone)
  ) {
    return <Redirect href="/(main)/choose-avatar" />;
  }

  return <>{children}</>;
}
