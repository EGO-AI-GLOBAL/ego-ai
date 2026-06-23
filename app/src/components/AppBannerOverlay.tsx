import React from "react";
import { View } from "react-native";
import { AppUpdateBanner } from "@/components/AppUpdateBanner";
import { SystemStatusBanner } from "@/components/SystemStatusBanner";

type Props = {
  children: React.ReactNode;
};

/**
 * Banners no fluxo normal (não overlay) — evita sumir ou não receber toque no iOS/Android.
 */
export function AppBannerOverlay({ children }: Props) {
  return (
    <View style={{ flex: 1 }}>
      <AppUpdateBanner />
      <SystemStatusBanner />
      <View style={{ flex: 1 }}>{children}</View>
    </View>
  );
}
