import { openShapeScan, shapeScanPromoCopy } from "@/constants/shapeScanPromo";
import React, { useCallback, useMemo } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

/**
 * Cross-promo ShapeScan (~60px). O pai (FreeFooterBanner) decide quando montar:
 * só FREE e só quando AdMob não tem fill.
 */
export function ShapeScanCrossPromoBanner() {
  const copy = useMemo(() => shapeScanPromoCopy(), []);

  const onPress = useCallback(() => {
    void openShapeScan();
  }, []);

  return (
    <View style={styles.wrap}>
      <Pressable
        onPress={onPress}
        style={({ pressed }) => [styles.bar, pressed && styles.barPressed]}
        accessibilityRole="button"
        accessibilityLabel="Abrir ShapeScan"
      >
        <Text style={styles.text} numberOfLines={2}>
          {copy}
        </Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    width: "100%",
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  bar: {
    minHeight: 52,
    maxHeight: 60,
    backgroundColor: "#00DF89",
    borderRadius: 10,
    paddingVertical: 8,
    paddingHorizontal: 12,
    justifyContent: "center",
  },
  barPressed: {
    opacity: 0.88,
  },
  text: {
    color: "#0A1A14",
    fontWeight: "700",
    fontSize: 13,
    lineHeight: 18,
  },
});
