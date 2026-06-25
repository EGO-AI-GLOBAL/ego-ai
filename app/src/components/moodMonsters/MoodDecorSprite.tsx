import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, type TextStyle } from "react-native";

type Props = {
  emoji: string;
  left: `${number}%`;
  top: number;
  size: number;
  delay?: number;
  sway?: boolean;
};

/** Decoração do jardim com flutuação suave (estilo Finch). */
export function MoodDecorSprite({ emoji, left, top, size, delay = 0, sway = false }: Props) {
  const bob = useRef(new Animated.Value(0)).current;
  const tilt = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const bobLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(bob, {
          toValue: 1,
          duration: 1400 + delay * 120,
          useNativeDriver: true,
        }),
        Animated.timing(bob, {
          toValue: 0,
          duration: 1400 + delay * 120,
          useNativeDriver: true,
        }),
      ])
    );
    bobLoop.start();
    let tiltLoop: Animated.CompositeAnimation | null = null;
    if (sway) {
      tiltLoop = Animated.loop(
        Animated.sequence([
          Animated.timing(tilt, { toValue: 1, duration: 2200, useNativeDriver: true }),
          Animated.timing(tilt, { toValue: 0, duration: 2200, useNativeDriver: true }),
        ])
      );
      tiltLoop.start();
    }
    return () => {
      bobLoop.stop();
      tiltLoop?.stop();
    };
  }, [bob, tilt, delay, sway]);

  const translateY = bob.interpolate({ inputRange: [0, 1], outputRange: [0, -5] });
  const rotate = tilt.interpolate({ inputRange: [0, 1], outputRange: ["-4deg", "4deg"] });

  return (
    <Animated.Text
      style={[
        styles.sprite,
        {
          left,
          top,
          fontSize: size,
          transform: [{ translateY }, { rotate }],
        } as TextStyle,
      ]}
    >
      {emoji}
    </Animated.Text>
  );
}

const styles = StyleSheet.create({
  sprite: { position: "absolute", zIndex: 2 },
});
