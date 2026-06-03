import "@/utils/webLocation";
import { initMonitoring } from "@/monitoring/errorReporter";
import { ErrorBoundary } from "@/monitoring/ErrorBoundary";
import { Stack } from "expo-router";

initMonitoring();
import { StatusBar } from "expo-status-bar";
import { Dimensions, useColorScheme } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/theme/ThemeContext";
import { useColors } from "@/theme/ThemeContext";

const webInitialMetrics = {
  insets: { top: 0, left: 0, right: 0, bottom: 0 },
  frame: {
    x: 0,
    y: 0,
    width: Dimensions.get("window").width,
    height: Dimensions.get("window").height,
  },
};

function RootNavigator() {
  const colors = useColors();
  const scheme = useColorScheme();
  return (
    <>
      <StatusBar style={scheme === "dark" ? "light" : "dark"} />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: colors.bg },
          animation: "fade",
        }}
      >
        <Stack.Screen name="(main)" />
        <Stack.Screen name="login" />
        <Stack.Screen name="signup" />
        <Stack.Screen name="forgot-password" />
        <Stack.Screen name="legal/[doc]" />
      </Stack>
    </>
  );
}

export default function RootLayout() {
  return (
    <ErrorBoundary>
      <SafeAreaProvider initialMetrics={webInitialMetrics}>
        <ThemeProvider>
          <AuthProvider>
            <RootNavigator />
          </AuthProvider>
        </ThemeProvider>
      </SafeAreaProvider>
    </ErrorBoundary>
  );
}
