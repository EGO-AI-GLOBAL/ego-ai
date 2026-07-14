import React, { useEffect, useRef, useState } from "react";
import {
  Animated,
  Modal,
  Pressable,
  StyleSheet,
  Switch,
  Text,
  View,
} from "react-native";
import * as Haptics from "expo-haptics";
import type { AppColors } from "@/theme/colors";
import { resolveCalmaClipKey } from "@/constants/calmaClipAssets";
import { CalmaClipPlayer } from "@/components/pausa/CalmaClipPlayer";

type Phase = "inhale" | "exhale";

type Props = {
  colors: AppColors;
  visible: boolean;
  assistantName: string;
  durationSeconds?: number;
  title?: string;
  subtitle?: string;
  inhaleSeconds?: number;
  exhaleSeconds?: number;
  /** key do exercício (breath44, sos, …) → vídeo WayIn. */
  clipKey?: string;
  onClose: () => void;
  onComplete: () => void;
};

export function PausaBreathSession({
  colors,
  visible,
  assistantName,
  durationSeconds = 60,
  title,
  subtitle,
  inhaleSeconds = 4,
  exhaleSeconds = 4,
  clipKey,
  onClose,
  onComplete,
}: Props) {
  const videoKey = resolveCalmaClipKey(clipKey);
  const total = Math.max(30, Math.min(180, durationSeconds));
  const phaseDur = Math.max(3, Math.min(8, inhaleSeconds));
  const exhaleDur = Math.max(3, Math.min(10, exhaleSeconds));
  const [secondsLeft, setSecondsLeft] = useState(total);
  const [phase, setPhase] = useState<Phase>("inhale");
  const [phaseCount, setPhaseCount] = useState(phaseDur);
  const [ambientOn, setAmbientOn] = useState(true);
  const scale = useRef(new Animated.Value(0.72)).current;
  const finishedRef = useRef(false);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!visible) {
      if (tickRef.current) clearInterval(tickRef.current);
      finishedRef.current = false;
      setSecondsLeft(total);
      setPhase("inhale");
      setPhaseCount(phaseDur);
      scale.setValue(0.72);
      return;
    }

    setSecondsLeft(total);
    finishedRef.current = false;
    tickRef.current = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          if (tickRef.current) clearInterval(tickRef.current);
          if (!finishedRef.current) {
            finishedRef.current = true;
            void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
            onComplete();
          }
          return 0;
        }
        return prev - 1;
      });
      setPhaseCount((prev) => {
        if (prev <= 1) {
          let nextDur = phaseDur;
          setPhase((p) => {
            const np = p === "inhale" ? "exhale" : "inhale";
            nextDur = np === "inhale" ? phaseDur : exhaleDur;
            if (ambientOn) {
              void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
            }
            return np;
          });
          return nextDur;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (tickRef.current) clearInterval(tickRef.current);
    };
  }, [visible, onComplete, scale, total, ambientOn, phaseDur, exhaleDur]);

  useEffect(() => {
    if (!visible) return;
    Animated.timing(scale, {
      toValue: phase === "inhale" ? 1 : 0.72,
      duration: (phase === "inhale" ? phaseDur : exhaleDur) * 1000,
      useNativeDriver: true,
    }).start();
  }, [phase, visible, scale, phaseDur, exhaleDur]);

  const phaseLabel = phase === "inhale" ? "Inspire…" : "Expire…";
  const titleSec = title || (total >= 120 ? "2 minutos" : "60 segundos");
  const subLine = subtitle || `Respiração ${phaseDur}–${exhaleDur} · solte os ombros`;

  return (
    <Modal visible={visible} animationType="fade" transparent onRequestClose={onClose}>
      <View style={[styles.backdrop, { backgroundColor: "rgba(8,6,20,0.88)" }]}>
        <View style={[styles.card, { backgroundColor: colors.bgCard, borderColor: colors.primary }]}>
          <Text style={[styles.badge, { color: colors.primary }]}>Calma 1 min 🌬️</Text>
          <Text style={[styles.title, { color: colors.text }]}>
            {title ? title : `${titleSec} com ${assistantName}`}
          </Text>
          <Text style={[styles.sub, { color: colors.textMuted }]}>{subLine}</Text>

          <View style={styles.ambientRow}>
            <Text style={[styles.ambientLabel, { color: colors.textMuted }]}>
              Modo discreto (sem vibração / som do clip)
            </Text>
            <Switch
              value={ambientOn}
              onValueChange={setAmbientOn}
              trackColor={{ false: colors.border, true: colors.primarySoft }}
              thumbColor={ambientOn ? colors.primary : colors.textMuted}
            />
          </View>

          <CalmaClipPlayer clipKey={videoKey} playing={visible} muted={!ambientOn} />

          <View style={styles.circleWrap}>
            <Animated.View
              style={[
                styles.circle,
                {
                  backgroundColor: colors.primaryTint,
                  borderColor: colors.primary,
                  transform: [{ scale }],
                },
              ]}
            />
            <View style={styles.circleCenter}>
              <Text style={[styles.phase, { color: colors.primary }]}>{phaseLabel}</Text>
              <Text style={[styles.timer, { color: colors.text }]}>{secondsLeft}s</Text>
            </View>
          </View>

          <Text style={[styles.hint, { color: colors.textMuted }]}>
            {phase === "inhale"
              ? "Encha o peito devagar pelo nariz."
              : "Solte o ar pela boca, sem pressa."}
          </Text>

          <Pressable
            onPress={onClose}
            style={[styles.closeBtn, { borderColor: colors.border }]}
          >
            <Text style={[styles.closeText, { color: colors.textMuted }]}>Sair</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    justifyContent: "center",
    padding: 20,
  },
  card: {
    borderRadius: 20,
    borderWidth: 1.5,
    padding: 22,
    alignItems: "center",
  },
  badge: {
    fontSize: 11,
    fontWeight: "900",
    letterSpacing: 0.5,
  },
  title: {
    fontSize: 20,
    fontWeight: "800",
    marginTop: 8,
    textAlign: "center",
  },
  sub: {
    fontSize: 13,
    marginTop: 4,
    textAlign: "center",
  },
  ambientRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    width: "100%",
    marginTop: 14,
    paddingHorizontal: 4,
  },
  ambientLabel: { fontSize: 12, fontWeight: "600" },
  circleWrap: {
    width: 200,
    height: 200,
    marginVertical: 20,
    alignItems: "center",
    justifyContent: "center",
  },
  circle: {
    position: "absolute",
    width: 180,
    height: 180,
    borderRadius: 90,
    borderWidth: 2,
  },
  circleCenter: {
    alignItems: "center",
  },
  phase: {
    fontSize: 16,
    fontWeight: "800",
  },
  timer: {
    fontSize: 36,
    fontWeight: "900",
    marginTop: 4,
  },
  hint: {
    fontSize: 13,
    lineHeight: 18,
    textAlign: "center",
    minHeight: 36,
  },
  closeBtn: {
    marginTop: 16,
    paddingVertical: 10,
    paddingHorizontal: 24,
    borderRadius: 10,
    borderWidth: 1,
  },
  closeText: {
    fontWeight: "700",
    fontSize: 14,
  },
});
