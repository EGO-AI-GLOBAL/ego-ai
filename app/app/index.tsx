import { Redirect, type Href } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";
import { COLORS } from "@/constants/config";
import { useAuth } from "@/context/AuthContext";
import { readFunnelNeedsCheckin } from "@/notifications/funnelEngagementReminders";
import { consumePostLoginRoute, type PostLoginRoute } from "@/storage/postLoginRoute";

const DEFAULT_HOME = "/(main)/daily-care" as Href;

export default function Index() {
  const { session, loading } = useAuth();
  const [postLogin, setPostLogin] = useState<PostLoginRoute | null | undefined>(undefined);
  const [homeHref, setHomeHref] = useState<Href>(DEFAULT_HOME);

  useEffect(() => {
    void Promise.all([consumePostLoginRoute(), readFunnelNeedsCheckin()]).then(
      ([route, needsCheckin]) => {
        setPostLogin(route);
        if (!route) {
          setHomeHref((needsCheckin ? "/(main)/daily-care" : "/(main)/chat") as Href);
        }
      }
    );
  }, []);

  if (loading || postLogin === undefined) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: COLORS.bg }}>
        <ActivityIndicator size="large" color={COLORS.primary} />
      </View>
    );
  }

  if (session?.access_token?.trim()) {
    return <Redirect href={(postLogin ?? homeHref ?? DEFAULT_HOME) as Href} />;
  }

  return <Redirect href="/login" />;
}
