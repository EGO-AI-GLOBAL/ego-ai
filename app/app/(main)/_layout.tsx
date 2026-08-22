import { Redirect, Stack, useRouter, useSegments, type Href } from "expo-router";
import { useEffect, useRef } from "react";
import { ActivityIndicator, View } from "react-native";
import { useAdMobBootstrap } from "@/ads/adMobBootstrap";
import { syncDailyCheckInNotification } from "@/utils/dailyCheckInNotification";
import { AppDrawer } from "@/components/AppDrawer";
import { PersonaGate } from "@/components/PersonaGate";
import { DashboardProvider } from "@/context/DashboardContext";
import { DrawerProvider } from "@/context/DrawerContext";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/hooks/useDashboard";
import { useDailyRitualNotifications } from "@/hooks/useDailyRitualNotifications";
import { refreshFunnelEngagementReminders } from "@/notifications/funnelEngagementReminders";
import { useColors } from "@/theme/ThemeContext";
import { shouldShowChatAds } from "@/utils/shouldShowChatAds";

function FunnelRemindersSync() {
  const { data } = useDashboard();
  const checkedToday = Boolean(data.daily_care?.checked_today);

  useEffect(() => {
    void refreshFunnelEngagementReminders({ checkedToday });
  }, [checkedToday]);

  return null;
}

function PendingInviteRedirect() {
  const router = useRouter();
  const { data, loading } = useDashboard();
  const redirected = useRef(false);

  useEffect(() => {
    if (loading || redirected.current) return;
    if ((data.pending_calendar_invites?.length ?? 0) > 0) {
      redirected.current = true;
      router.replace("/(main)/agenda" as Href);
    }
  }, [loading, data.pending_calendar_invites?.length, router]);

  return null;
}

function MainShell() {
  const colors = useColors();
  const segments = useSegments();
  const hideDrawer = segments.includes("choose-avatar");
  const { data } = useDashboard();
  useDailyRitualNotifications();
  useAdMobBootstrap(shouldShowChatAds(data?.access));

  return (
    <PersonaGate>
      <FunnelRemindersSync />
      <PendingInviteRedirect />
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
