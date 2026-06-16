import { Redirect, Stack, useSegments } from "expo-router";
import { useEffect } from "react";
import { ActivityIndicator, View } from "react-native";
import { syncDailyCheckInNotification } from "@/utils/dailyCheckInNotification";
import { AppDrawer } from "@/components/AppDrawer";
import { PersonaGate } from "@/components/PersonaGate";
import { DashboardProvider } from "@/context/DashboardContext";
import { DrawerProvider } from "@/context/DrawerContext";
import { useAuth } from "@/context/AuthContext";
import { useDailyRitualNotifications } from "@/hooks/useDailyRitualNotifications";
import { useColors } from "@/theme/ThemeContext";

function MainShell() {
  const colors = useColors();
  const segments = useSegments();
  const hideDrawer = segments.includes("choose-avatar");
  useDailyRitualNotifications();

  return (
    <PersonaGate>
      <DrawerProvider>
        <>
          <View style={{ flex: 1, backgroundColor: colors.bg }}>
            <Stack
              screenOptions={{
                headerShown: false,
                contentStyle: { backgroundColor: colors.bg },
                animation: "fade",
              }}
            />
          </View>
          {!hideDrawer ? <AppDrawer /> : null}
        </>
      </DrawerProvider>
    </PersonaGate>
  );
}

export default function MainLayout() {
  const colors = useColors();
  const { session, loading } = useAuth();

  useEffect(() => {
    if (session?.access_token?.trim()) {
      void syncDailyCheckInNotification();
    }
  }, [session?.access_token]);

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

  if (!session?.access_token?.trim()) {
    return <Redirect href="/login" />;
  }

  return (
    <DashboardProvider>
      <MainShell />
    </DashboardProvider>
  );
}
