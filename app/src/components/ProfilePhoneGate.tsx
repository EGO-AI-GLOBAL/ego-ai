import { Redirect, useSegments } from "expo-router";
import React from "react";
import { ActivityIndicator, View } from "react-native";
import { useDashboard } from "@/hooks/useDashboard";
import { useColors } from "@/theme/ThemeContext";
import { isProfilePhoneMissing } from "@/utils/profileComplete";

type Props = {
  children: React.ReactNode;
};

/** Contas antigas sem telefone — obriga a completar antes do resto do app. */
export function ProfilePhoneGate({ children }: Props) {
  const colors = useColors();
  const { data, loading } = useDashboard();
  const segments = useSegments();
  const onCompleteProfile = segments.includes("complete-profile");

  if (loading) {
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

  const missing = isProfilePhoneMissing(data.me);

  if (missing && !onCompleteProfile) {
    return <Redirect href="/(main)/complete-profile" />;
  }

  if (!missing && onCompleteProfile) {
    return <Redirect href="/(main)/chat" />;
  }

  return <>{children}</>;
}
