import { Redirect, type Href } from "expo-router";
import { ActivityIndicator, View } from "react-native";
import { COLORS } from "@/constants/config";
import { useAuth } from "@/context/AuthContext";

export default function Index() {
  const { session, loading } = useAuth();

  if (loading) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: COLORS.bg }}>
        <ActivityIndicator size="large" color={COLORS.primary} />
      </View>
    );
  }

  if (session?.access_token?.trim()) {
    return <Redirect href={"/(main)/chat" as Href} />;
  }

  return <Redirect href="/login" />;
}
