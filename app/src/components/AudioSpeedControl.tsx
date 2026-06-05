import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import {
  AUDIO_SPEED_OPTIONS,
  AUDIO_SPEED_OPTIONS_ALL,
  AUDIO_SPEED_OPTIONS_PAID,
  formatAudioSpeed,
  type AudioPlaybackSpeed,
} from "@/constants/audioSpeed";
import type { AppColors } from "@/theme/colors";

type Props = {
  colors: AppColors;
  value: AudioPlaybackSpeed;
  onChange: (speed: AudioPlaybackSpeed) => void;
  disabled?: boolean;
  allowedSpeeds?: AudioPlaybackSpeed[];
  include2x?: boolean;
};

function isPlaybackSpeed(n: number): n is AudioPlaybackSpeed {
  return n === 1 || n === 1.5 || n === 2;
}

export function AudioSpeedControl({
  colors,
  value,
  onChange,
  disabled,
  allowedSpeeds,
  include2x = false,
}: Props) {
  const options: AudioPlaybackSpeed[] = allowedSpeeds?.length
    ? allowedSpeeds.filter(isPlaybackSpeed)
    : include2x
      ? AUDIO_SPEED_OPTIONS_ALL
      : AUDIO_SPEED_OPTIONS_PAID;

  // Só mostra chips de aceleração (1x é o padrão sem botão).
  const chips = options.filter((s) => s !== 1);
  if (chips.length === 0) {
    return null;
  }

  return (
    <View style={styles.row}>
      {chips.map((speed) => {
        const selected = value === speed;
        return (
          <Pressable
            key={speed}
            onPress={() => onChange(selected ? 1 : speed)}
            disabled={disabled}
            style={({ pressed }) => [
              styles.chip,
              {
                borderColor: selected ? colors.primary : colors.border,
                backgroundColor: selected ? colors.userBubble : colors.bgCard,
                opacity: disabled ? 0.45 : pressed ? 0.85 : 1,
              },
            ]}
            accessibilityRole="button"
            accessibilityLabel={`Velocidade ${formatAudioSpeed(speed)}`}
            accessibilityState={{ selected, disabled: Boolean(disabled) }}
          >
            <Text
              style={[
                styles.label,
                { color: selected ? colors.primary : colors.textMuted },
              ]}
            >
              {formatAudioSpeed(speed)}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", gap: 6 },
  chip: {
    minWidth: 44,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    borderWidth: 1,
    alignItems: "center",
  },
  label: { fontSize: 12, fontWeight: "700" },
});
