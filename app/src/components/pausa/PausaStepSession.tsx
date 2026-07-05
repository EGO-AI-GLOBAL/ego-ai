import React, { useEffect, useRef, useState } from "react";
import { Modal, Pressable, StyleSheet, Text, View } from "react-native";
import * as Haptics from "expo-haptics";
import type { PausaExerciseStep } from "@/api/types";
import type { AppColors } from "@/theme/colors";

type Props = {
  colors: AppColors;
  visible: boolean;
  title: string;
  subtitle: string;
  steps: PausaExerciseStep[];
  onClose: () => void;
  onComplete: () => void;
};

export function PausaStepSession({
  colors,
  visible,
  title,
  subtitle,
  steps,
  onClose,
  onComplete,
}: Props) {
  const safeSteps = steps.length > 0 ? steps : [{ text: "Respire com calma.", seconds: 10 }];
  const [stepIdx, setStepIdx] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(safeSteps[0]?.seconds ?? 8);
  const finishedRef = useRef(false);
  const stepIdxRef = useRef(0);

  useEffect(() => {
    if (!visible) {
      finishedRef.current = false;
      stepIdxRef.current = 0;
      setStepIdx(0);
      setSecondsLeft(safeSteps[0]?.seconds ?? 8);
      return;
    }
    finishedRef.current = false;
    stepIdxRef.current = 0;
    setStepIdx(0);
    setSecondsLeft(safeSteps[0]?.seconds ?? 8);
  }, [visible, safeSteps]);

  useEffect(() => {
    if (!visible) return;
    const tick = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev > 1) return prev - 1;
        const nextIdx = stepIdxRef.current + 1;
        if (nextIdx >= safeSteps.length) {
          if (!finishedRef.current) {
            finishedRef.current = true;
            void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
            onComplete();
          }
          return 0;
        }
        stepIdxRef.current = nextIdx;
        setStepIdx(nextIdx);
        void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        return safeSteps[nextIdx]?.seconds ?? 8;
      });
    }, 1000);
    return () => clearInterval(tick);
  }, [visible, safeSteps, onComplete]);

  const current = safeSteps[Math.min(stepIdx, safeSteps.length - 1)];

  return (
    <Modal visible={visible} animationType="fade" transparent onRequestClose={onClose}>
      <View style={[styles.backdrop, { backgroundColor: "rgba(8,6,20,0.88)" }]}>
        <View style={[styles.card, { backgroundColor: colors.bgCard, borderColor: colors.primary }]}>
          <Text style={[styles.badge, { color: colors.primary }]}>PAUSA DE HOJE</Text>
          <Text style={[styles.title, { color: colors.text }]}>{title}</Text>
          <Text style={[styles.sub, { color: colors.textMuted }]}>{subtitle}</Text>

          <View style={[styles.stepBox, { backgroundColor: colors.primaryTint }]}>
            <Text style={[styles.stepText, { color: colors.text }]}>{current?.text}</Text>
            <Text style={[styles.timer, { color: colors.primary }]}>{secondsLeft}s</Text>
          </View>

          <Text style={[styles.progress, { color: colors.textMuted }]}>
            Passo {Math.min(stepIdx + 1, safeSteps.length)} de {safeSteps.length}
          </Text>

          <Pressable onPress={onClose} style={[styles.closeBtn, { borderColor: colors.border }]}>
            <Text style={[styles.closeText, { color: colors.textMuted }]}>Sair</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, justifyContent: "center", padding: 20 },
  card: { borderRadius: 18, borderWidth: 1.5, padding: 20 },
  badge: { fontSize: 10, fontWeight: "900", letterSpacing: 0.5 },
  title: { fontSize: 20, fontWeight: "900", marginTop: 8 },
  sub: { fontSize: 13, lineHeight: 18, marginTop: 6 },
  stepBox: {
    borderRadius: 14,
    padding: 18,
    marginTop: 18,
    minHeight: 120,
    justifyContent: "center",
  },
  stepText: { fontSize: 17, lineHeight: 24, fontWeight: "700", textAlign: "center" },
  timer: { fontSize: 28, fontWeight: "900", textAlign: "center", marginTop: 12 },
  progress: { fontSize: 12, textAlign: "center", marginTop: 12, fontWeight: "700" },
  closeBtn: {
    marginTop: 16,
    borderRadius: 12,
    borderWidth: 1,
    paddingVertical: 12,
    alignItems: "center",
  },
  closeText: { fontWeight: "700", fontSize: 14 },
});
