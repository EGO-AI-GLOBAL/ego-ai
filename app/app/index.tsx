import { Redirect, type Href } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";
import { COLORS } from "@/constants/config";
import { useAuth } from "@/context/AuthContext";
import { readFunnelNeedsCheckin } from "@/notifications/funnelEngagementReminders";
import { consumePostLoginRoute, type PostLoginRoute } from "@/storage/postLoginRoute";

export default function Index() {
  const { session, loading } = useAuth();
  const [postLogin, setPostLogin] = useState<PostLoginRoute | null | undefined>(undefined);
  const [homeHref, setHomeHref] = useState<Href | null>(null);

  useEffect(() => {
    void consumePostLoginRoute().then(async (route) => {
      setPostLogin(route);
      if (route) return;
      const needsCheckin = await readFunnelNeedsCheckin();
      setHomeHref((needsCheckin ? "/(main)/daily-care" : "/(main)/chat") as Href);
    });
  }, []);

  if (loading || postLogin === undefined || (session?.access_token?.trim() && !postLogin && homeHref === null)) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: COLORS.bg }}>
        <ActivityIndicator size="large" color={COLORS.primary} />
      </View>
    );
  }

  if (session?.access_token?.trim()) {
    return <Redirect href={(postLogin ?? homeHref ?? "/(main)/chat") as Href} />;
  }

  return <Redirect href="/login" />;
}
