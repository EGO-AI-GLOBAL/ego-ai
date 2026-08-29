import { Redirect, type Href } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";
import { COLORS } from "@/constants/config";
import { readFunnelNeedsCheckin } from "@/notifications/funnelEngagementReminders";

/** Alinha com app/index.tsx — Monstrinhos se falta check-in; chat se já fez hoje. */
export default function MainIndex() {
  const [href, setHref] = useState<Href | null>(null);

  useEffect(() => {
    void readFunnelNeedsCheckin().then((needs) => {
      setHref((needs ? "/(main)/daily-care" : "/(main)/chat") as Href);
    });
  }, []);

  if (!href) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: COLORS.bg }}>
        <ActivityIndicator size="large" color={COLORS.primary} />
      </View>
    );
  }

  return <Redirect href={href} />;
}
