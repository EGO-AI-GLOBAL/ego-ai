import { Redirect, type Href } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";
import { COLORS } from "@/constants/config";
import { useAuth } from "@/context/AuthContext";
import { consumePostLoginRoute, type PostLoginRoute } from "@/storage/postLoginRoute";

export default function Index() {
  const { session, loading } = useAuth();
  const [postLogin, setPostLogin] = useState<PostLoginRoute | null | undefined>(undefined);

  useEffect(() => {
    void consumePostLoginRoute().then((route) => setPostLogin(route));
  }, []);

  if (loading || postLogin === undefined) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: COLORS.bg }}>
        <ActivityIndicator size="large" color={COLORS.primary} />
      </View>
    );
  }

  if (session?.access_token?.trim()) {
    return <Redirect href={(postLogin ?? "/(main)/chat") as Href} />;
  }

  return <Redirect href="/login" />;
}
