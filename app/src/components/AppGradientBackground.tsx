import { LinearGradient } from "expo-linear-gradient";
import React from "react";
import { StyleSheet, View, type StyleProp, type ViewStyle } from "react-native";
import { useColors } from "@/theme/ThemeContext";

type Props = {
  children?: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  /** auth = login/signup · chat = fundo sutil no chat */
  variant?: "auth" | "chat" | "default";
};

export function AppGradientBackground({
  children,
  style,
  variant = "default",
}: Props) {
  const colors = useColors();
  const stops =
    variant === "auth"
      ? ([colors.gradientStart, colors.gradientMid, colors.gradientEnd] as const)
      : variant === "chat"
        ? ([colors.gradientStart, colors.bg, colors.bg] as const)
        : ([colors.gradientStart, colors.gradientEnd] as const);

  return (
    <View style={[styles.fill, style]}>
      <LinearGradient
        colors={[...stops]}
        start={{ x: 0.1, y: 0 }}
        end={{ x: 0.9, y: 1 }}
        style={StyleSheet.absoluteFill}
      />
      {variant === "auth" ? (
        <View
          style={[
            styles.glowOrb,
            { backgroundColor: colors.glowPrimary, shadowColor: colors.glowCyan },
          ]}
        />
      ) : null}
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  glowOrb: {
    position: "absolute",
    top: "12%",
    alignSelf: "center",
    width: 220,
    height: 220,
    borderRadius: 110,
    opacity: 0.22,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.85,
    shadowRadius: 48,
    elevation: 0,
  },
});
