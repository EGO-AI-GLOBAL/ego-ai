import React, { useEffect, useRef, useState } from "react";
import {
  Animated,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import * as Haptics from "expo-haptics";
import type { AppColors } from "@/theme/colors";

const SESSION_SECONDS = 60;
const PHASE_SECONDS = 4;

type Phase = "inhale" | "exhale";

type Props = {
  colors: AppColors;
  visible: boolean;
  assistantName: string;
  onClose: () => void;
  onComplete: () => void;
};

export function PausaBreathSession({
  colors,
  visible,
  assistantName,
  onClose,
  onComplete,
}: Props) {
  const [secondsLeft, setSecondsLeft] = useState(SESSION_SECONDS);
  const [phase, setPhase] = useState<Phase>("inhale");
  const [phaseCount, setPhaseCount] = useState(PHASE_SECONDS);
  const scale = useRef(new Animated.Value(0.72)).current;
  const finishedRef = useRef(false);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!visible) {
      if (tickRef.current) clearInterval(tickRef.current);
      finishedRef.current = false;
      setSecondsLeft(SESSION_SECONDS);
      setPhase("inhale");
      setPhaseCount(PHASE_SECONDS);
      scale.setValue(0.72);
      return;
    }

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
          setPhase((p) => (p === "inhale" ? "exhale" : "inhale"));
          return PHASE_SECONDS;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (tickRef.current) clearInterval(tickRef.current);
    };
  }, [visible, onComplete, scale]);

  useEffect(() => {
    if (!visible) return;
    Animated.timing(scale, {
      toValue: phase === "inhale" ? 1 : 0.72,
      duration: PHASE_SECONDS * 1000,
      useNativeDriver: true,
    }).start();
  }, [phase, visible, scale]);

  const phaseLabel = phase === "inhale" ? "Inspire…" : "Expire…";

  return (
    <Modal visible={visible} animationType="fade" transparent onRequestClose={onClose}>
      <View style={[styles.backdrop, { backgroundColor: "rgba(8,6,20,0.88)" }]}>
        <View style={[styles.card, { backgroundColor: colors.bgCard, borderColor: colors.primary }]}>
          <Text style={[styles.badge, { color: colors.primary }]}>PAUSA EGO 🌬️</Text>
          <Text style={[styles.title, { color: colors.text }]}>
            60 segundos com {assistantName}
          </Text>
          <Text style={[styles.sub, { color: colors.textMuted }]}>
            Respiração 4–4 · solte os ombros
          </Text>

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
  circleWrap: {
    width: 200,
    height: 200,
    marginVertical: 24,
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
