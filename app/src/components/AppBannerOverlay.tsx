import React from "react";
import { View } from "react-native";
import { AppForceUpdateGate } from "@/components/AppForceUpdateGate";
import { AppUpdateBanner } from "@/components/AppUpdateBanner";
import { SystemStatusBanner } from "@/components/SystemStatusBanner";

type Props = {
  children: React.ReactNode;
};

/**
 * Banners no fluxo normal — force update = modal bloqueante (sem fechar).
 */
export function AppBannerOverlay({ children }: Props) {
  return (
    <View style={{ flex: 1 }}>
      <AppForceUpdateGate />
      <AppUpdateBanner />
      <SystemStatusBanner />
      <View style={{ flex: 1 }}>{children}</View>
    </View>
  );
}
