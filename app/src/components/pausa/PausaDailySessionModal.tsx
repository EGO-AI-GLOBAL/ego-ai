import React, { useRef, useState } from "react";
import type { PausaDailyExercise } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { PausaBreathSession } from "@/components/pausa/PausaBreathSession";
import { PausaStepSession } from "@/components/pausa/PausaStepSession";

type Props = {
  colors: AppColors;
  exercise: PausaDailyExercise;
  assistantName: string;
  visible: boolean;
  onClose: () => void;
  onComplete: (kind: string) => void;
  sosMode?: boolean;
};

/** Abre sessão guiada conforme exercício diário (respiração ou passos). */
export function PausaDailySessionModal({
  colors,
  exercise,
  assistantName,
  visible,
  onClose,
  onComplete,
  sosMode = false,
}: Props) {
  const kindRef = useRef(exercise.key);

  const finish = () => {
    onComplete(sosMode ? "sos" : kindRef.current);
  };

  if (sosMode) {
    return (
      <PausaBreathSession
        colors={colors}
        visible={visible}
        assistantName={assistantName}
        durationSeconds={60}
        title="SOS — respire comigo"
        subtitle="Um minuto para acalmar agora"
        onClose={onClose}
        onComplete={finish}
      />
    );
  }

  if (exercise.mode === "steps") {
    return (
      <PausaStepSession
        colors={colors}
        visible={visible}
        title={exercise.title}
        subtitle={exercise.subtitle}
        steps={exercise.steps ?? []}
        onClose={onClose}
        onComplete={finish}
      />
    );
  }

  return (
    <PausaBreathSession
      colors={colors}
      visible={visible}
      assistantName={assistantName}
      durationSeconds={exercise.duration_seconds}
      title={exercise.title}
      subtitle={exercise.subtitle}
      inhaleSeconds={exercise.breath_inhale ?? 4}
      exhaleSeconds={exercise.breath_exhale ?? 4}
      onClose={onClose}
      onComplete={finish}
    />
  );
}

/** Hook mínimo para abrir/fechar sessão PAUSA. */
export function usePausaSessionLauncher() {
  const [open, setOpen] = useState(false);
  const [sos, setSos] = useState(false);

  return {
    sessionOpen: open,
    sosMode: sos,
    openDaily: () => {
      setSos(false);
      setOpen(true);
    },
    openSos: () => {
      setSos(true);
      setOpen(true);
    },
    closeSession: () => setOpen(false),
  };
}
