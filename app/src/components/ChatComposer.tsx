import React, { useEffect, useRef } from "react";
import {
  ActivityIndicator,
  Animated,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useColors } from "@/theme/ThemeContext";

function micHaptic(): void {
  if (Platform.OS === "web") return;
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const Haptics = require("expo-haptics") as {
      impactAsync?: (style: number) => Promise<void>;
      ImpactFeedbackStyle?: { Medium: number };
    };
    void Haptics.impactAsync?.(Haptics.ImpactFeedbackStyle?.Medium ?? 1);
  } catch {
    /* expo-haptics opcional */
  }
}

type Props = {
  value: string;
  onChangeText: (t: string) => void;
  onSend: () => void;
  sending: boolean;
  isRecording?: boolean;
  micSessionActive?: boolean;
  onMicPressIn?: () => void;
  onMicPressOut?: () => void;
  onMicPress?: () => void;
  voiceReady?: boolean;
  /** true só depois do 1.º toque terminar — evita seta no mesmo gesto (iOS + Android). */
  voiceSendReady?: boolean;
  error?: string | null;
  notice?: string | null;
  onPdfPress?: () => void;
  pdfLoading?: boolean;
  pdfActive?: boolean;
  pdfPartCount?: number;
  onInputFocus?: () => void;
  placeholder?: string;
};

function VoiceWaveBars({ color }: { color: string }) {
  const bars = [
    useRef(new Animated.Value(0.35)).current,
    useRef(new Animated.Value(0.65)).current,
    useRef(new Animated.Value(0.45)).current,
    useRef(new Animated.Value(0.8)).current,
    useRef(new Animated.Value(0.5)).current,
  ];

  useEffect(() => {
    const loops = bars.map((bar, i) =>
      Animated.loop(
        Animated.sequence([
          Animated.timing(bar, {
            toValue: 0.2 + ((i * 17) % 70) / 100,
            duration: 280 + i * 40,
            useNativeDriver: true,
          }),
          Animated.timing(bar, {
            toValue: 0.85 - ((i * 11) % 40) / 100,
            duration: 320 + i * 35,
            useNativeDriver: true,
          }),
        ])
      )
    );
    loops.forEach((l) => l.start());
    return () => loops.forEach((l) => l.stop());
  }, [bars]);

  return (
    <View style={styles.waveRow} accessibilityElementsHidden>
      {bars.map((bar, i) => (
        <Animated.View
          key={i}
          style={[
            styles.waveBar,
            {
              backgroundColor: color,
              transform: [{ scaleY: bar }],
            },
          ]}
        />
      ))}
    </View>
  );
}

export function ChatComposer({
  value,
  onChangeText,
  onSend,
  sending,
  isRecording,
  micSessionActive,
  onMicPress,
  voiceReady = true,
  voiceSendReady = false,
  error,
  notice,
  onPdfPress,
  pdfLoading,
  pdfActive,
  pdfPartCount,
  onInputFocus,
  placeholder = "Mensagem…",
}: Props) {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const isWeb = Platform.OS === "web";
  const bottomPad = Math.max(insets.bottom, isWeb ? 12 : 8);
  const hasText = value.trim().length > 0;
  const voiceUiActive = Boolean(isRecording || micSessionActive);
  const showArrow = hasText || (voiceUiActive && voiceSendReady);
  const sendDisabled = sending || (!voiceUiActive && !hasText);
  /** Um único botão — mic vira seta no mesmo sítio, sem trocar Pressable (envio fantasma). */
  const micGestureRef = useRef(false);

  const onTrailingPress = () => {
    if (sending) return;
    if (showArrow) {
      if (micGestureRef.current) {
        micGestureRef.current = false;
        return;
      }
      if (!sendDisabled) onSend();
      return;
    }
    micGestureRef.current = false;
    onMicTap();
  };

  const onMicTap = () => {
    if (sending) return;
    micHaptic();
    void onMicPress?.();
  };

  return (
    <View
      style={[
        styles.outer,
        {
          paddingBottom: bottomPad + 6,
        },
      ]}
    >
      <View
        style={[
          styles.floatShell,
          {
            backgroundColor: colors.glassBg,
            borderColor: colors.glassBorder,
            shadowColor: colors.primary,
          },
        ]}
      >
      <View style={styles.composerRow}>
        {onPdfPress ? (
          <Pressable
            onPress={onPdfPress}
            disabled={sending || pdfLoading}
            style={({ pressed }) => [
              styles.docBtn,
              {
                borderColor: pdfActive ? colors.primary : colors.border,
                backgroundColor: pdfActive ? colors.primaryTint : colors.bgCard,
                opacity: sending || pdfLoading ? 0.5 : pressed ? 0.85 : 1,
              },
            ]}
            accessibilityRole="button"
            accessibilityLabel={
              pdfPartCount && pdfPartCount > 0
                ? `Documento anexado, ${pdfPartCount} partes`
                : "Anexar documento ou foto"
            }
          >
            {pdfLoading ? (
              <ActivityIndicator color={colors.primary} size="small" />
            ) : (
              <Ionicons
                name={pdfActive ? "document" : "document-outline"}
                size={22}
                color={colors.primary}
              />
            )}
          </Pressable>
        ) : null}
      <View
        style={[
          styles.inputWrap,
          {
            flex: 1,
            backgroundColor: colors.bgCard,
            borderColor: voiceUiActive ? colors.primary : colors.border,
          },
        ]}
      >
        {voiceUiActive ? (
          <View style={styles.waveSlot}>
            {isRecording ? <VoiceWaveBars color={colors.primary} /> : null}
          </View>
        ) : null}

        <TextInput
          style={[
            styles.input,
            {
              color: colors.text,
              paddingRight: voiceUiActive ? 52 : 48,
            },
          ]}
          placeholder={voiceUiActive ? "A ouvir…" : placeholder}
          placeholderTextColor={colors.textMuted}
          value={value}
          onChangeText={onChangeText}
          onFocus={onInputFocus}
          editable={!sending && !voiceUiActive}
          multiline
          onSubmitEditing={() => {
            if (!sendDisabled) onSend();
          }}
          blurOnSubmit={false}
          returnKeyType="send"
        />

        <View style={styles.trailing}>
          {sending ? (
            <ActivityIndicator color={colors.primary} size="small" />
          ) : (
            <Pressable
              style={[
                styles.actionBtn,
                showArrow || voiceUiActive ? styles.sendCircle : styles.micCircle,
                {
                  backgroundColor: showArrow
                    ? colors.primary
                    : voiceUiActive
                      ? colors.primary
                      : colors.micBg,
                  borderColor: showArrow || voiceUiActive ? colors.primary : colors.micBg,
                },
                showArrow && sendDisabled && styles.actionDisabled,
              ]}
              onPressIn={() => {
                if (!voiceUiActive && !hasText) micGestureRef.current = true;
              }}
              onPress={onTrailingPress}
              disabled={sending || (showArrow && sendDisabled)}
              accessibilityRole="button"
              accessibilityLabel={
                showArrow
                  ? voiceUiActive
                    ? "Enviar mensagem de voz"
                    : "Enviar mensagem"
                  : voiceUiActive
                    ? "A gravar — aguarde a seta para enviar"
                    : "Microfone — toque para gravar"
              }
            >
              <Ionicons
                name={showArrow ? "arrow-up" : "mic"}
                size={showArrow ? 22 : 26}
                color="#fff"
              />
            </Pressable>
          )}
        </View>
      </View>
      </View>
      </View>

      {voiceUiActive ? (
        <Text style={[styles.recordingHint, { color: colors.primary }]}>
          {!voiceSendReady
            ? "A gravar… fale agora"
            : voiceReady
              ? "A gravar… toque na seta ↑ para enviar"
              : "A preparar microfone…"}
        </Text>
      ) : null}
      {notice && !voiceUiActive ? (
        <Text style={[styles.notice, { color: colors.success }]}>{notice}</Text>
      ) : null}
      {error ? <Text style={[styles.error, { color: colors.danger }]}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  outer: {
    flexShrink: 0,
    paddingHorizontal: 10,
    paddingTop: 4,
  },
  floatShell: {
    borderRadius: 28,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingTop: 10,
    paddingBottom: 6,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.16,
    shadowRadius: 14,
    elevation: 8,
  },
  composerRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 8,
  },
  docBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    borderWidth: StyleSheet.hairlineWidth,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 2,
  },
  inputWrap: {
    flexDirection: "row",
    alignItems: "center",
    minHeight: 48,
    borderRadius: 24,
    borderWidth: StyleSheet.hairlineWidth,
    paddingLeft: 14,
    paddingVertical: 4,
    ...(Platform.OS === "web" ? ({ touchAction: "manipulation" } as object) : {}),
  },
  waveSlot: {
    paddingRight: 6,
    justifyContent: "center",
  },
  waveRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 3,
    height: 22,
  },
  waveBar: {
    width: 3,
    height: 22,
    borderRadius: 2,
    opacity: 0.85,
  },
  input: {
    flex: 1,
    minHeight: 40,
    maxHeight: 100,
    paddingVertical: 8,
    fontSize: 16,
    borderWidth: 0,
    backgroundColor: "transparent",
  },
  trailing: {
    position: "absolute",
    right: 4,
    top: 0,
    bottom: 0,
    justifyContent: "center",
    alignItems: "center",
    width: 52,
  },
  actionBtn: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: "center",
    justifyContent: "center",
  },
  sendCircle: {},
  micCircle: {
    borderWidth: 0,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.12,
    shadowRadius: 4,
    elevation: 3,
  },
  actionDisabled: { opacity: 0.45 },
  recordingHint: {
    fontSize: 13,
    marginTop: 8,
    textAlign: "center",
    fontWeight: "600",
  },
  notice: { fontSize: 12, marginTop: 6, textAlign: "center" },
  error: { fontSize: 12, marginTop: 6, textAlign: "center" },
});
