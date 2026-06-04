import React from "react";
import { Image, StyleSheet, Text, View, type ImageStyle, type StyleProp } from "react-native";

const logoBrand = require("../../assets/logo-brand.png");
const logoIcon = require("../../assets/icon.png");

type EgoLogoProps = {
  /** Banner completo (login) ou só o ícone quadrado (menu). */
  variant?: "brand" | "icon";
  width?: number;
  showTagline?: boolean;
  style?: StyleProp<ImageStyle>;
};

export function EgoLogo({
  variant = "brand",
  width = 280,
  showTagline = false,
  style,
}: EgoLogoProps) {
  if (variant === "icon") {
    const size = width;
    return (
      <Image
        source={logoIcon}
        style={[{ width: size, height: size, borderRadius: size * 0.22 }, style]}
        resizeMode="contain"
        accessibilityLabel="Ego-IA"
      />
    );
  }

  const height = Math.round(width * (558 / 1024));
  return (
    <View style={styles.brandWrap}>
      <Image
        source={logoBrand}
        style={[{ width, height }, style]}
        resizeMode="contain"
        accessibilityLabel="Ego-IA — O seu amigo no bolso"
      />
      {showTagline ? (
        <Text style={styles.tagline}>O seu amigo no bolso</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  brandWrap: { alignItems: "center" },
  tagline: {
    marginTop: 8,
    fontSize: 14,
    fontWeight: "500",
    color: "#94A3B8",
    letterSpacing: 0.2,
  },
});
