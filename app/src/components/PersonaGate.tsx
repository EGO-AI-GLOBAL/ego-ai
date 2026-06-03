import { Redirect, useSegments } from "expo-router";
import React from "react";
import { ActivityIndicator, View } from "react-native";
import { useDashboard } from "@/hooks/useDashboard";
import { useColors } from "@/theme/ThemeContext";

type Props = {
  children: React.ReactNode;
};

export function PersonaGate({ children }: Props) {
  const colors = useColors();
  const { data, loading, personaGateOk } = useDashboard();
  const segments = useSegments();
  const onChooseAvatar = segments.includes("choose-avatar");
  const configured = personaGateOk;

  if (loading && !data.me) {
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
