import { Asset } from "expo-asset";
import { LinearGradient } from "expo-linear-gradient";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Platform, StyleSheet, Text, View } from "react-native";
import {
  clipActionForGoalKey,
  monsterClipModule,
  type MonsterClipAction,
} from "@/constants/monsterClipAssets";
import { moodKeyOrDefault, resolveMoodLabel } from "@/constants/moodMonsters";
import type { AppColors } from "@/theme/colors";
import { MoodMonsterIllustration } from "./MoodMonsterIllustration";

function loadExpoAv(): typeof import("expo-av") | null {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    return require("expo-av");
  } catch {
    return null;
  }
}

export type MonsterPetPlayRequest = {
  action: MonsterClipAction;
  /** Incrementar a cada play para repetir o mesmo action. */
  nonce: number;
};

type Props = {
  colors: AppColors;
  /** Humor activo (check-in ou preview no PressIn). */
  moodKey?: string;
  moods?: { key: string; label: string }[];
  playRequest?: MonsterPetPlayRequest | null;
  onPlayDone?: () => void;
};

/**
 * Pet sticky no topo dos Monstrinhos.
 * Idle: loop infinito do 01-idle da cor do humor.
 * Acção (humor/missão): one-shot → volta ao idle.
 */
export function MoodMonsterStickyPet({
  colors,
  moodKey,
  moods,
  playRequest,
  onPlayDone,
}: Props) {
  const av = useMemo(() => loadExpoAv(), []);
  const key = moodKeyOrDefault(moodKey);
  const label = resolveMoodLabel(moods, key);

  const [action, setAction] = useState<MonsterClipAction>("idle");
  const [videoUri, setVideoUri] = useState<string | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [ready, setReady] = useState(false);
  const lastNonce = useRef(0);
  const videoRef = useRef<{
    setPositionAsync?: (n: number) => Promise<void>;
    playAsync?: () => Promise<void>;
  } | null>(null);

  useEffect(() => {
    if (!playRequest) return;
    if (playRequest.nonce === lastNonce.current) return;
    lastNonce.current = playRequest.nonce;
    setAction(playRequest.action === "idle" ? "idle" : playRequest.action);
  }, [playRequest]);

  useEffect(() => {
    let cancelled = false;
    setVideoUri(null);
    setReady(false);
    setLoadError(false);

    void (async () => {
      try {
        const mod = monsterClipModule(key, action);
        const asset = Asset.fromModule(mod);
        await asset.downloadAsync();
        if (!cancelled) {
          setVideoUri(asset.localUri || asset.uri);
        }
      } catch {
        if (!cancelled) setLoadError(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [key, action]);

  const isIdle = action === "idle";

  const finishOneShot = useCallback(() => {
    setAction("idle");
    onPlayDone?.();
  }, [onPlayDone]);

  const onStatus = useCallback(
    (status: { isLoaded?: boolean; didJustFinish?: boolean }) => {
      if (!isIdle && status?.isLoaded && status.didJustFinish) {
        finishOneShot();
      }
    },
    [isIdle, finishOneShot]
  );

  // Fundo do vídeo = verde de jardim (não chromakey). Palco na mesma família para não “quebrar”.
  const gardenGreen = ["#6BB36E", "#8BC98A", "#A8D4A0"] as const;

  if (!av?.Video || loadError || Platform.OS === "web") {
    return (
      <View style={[styles.wrap, { borderColor: "#5A9E62", backgroundColor: "#6BB36E" }]}>
        <LinearGradient colors={[...gardenGreen]} style={styles.stage}>
          <MoodMonsterIllustration moodKey={key} size={128} celebrate={!isIdle} />
          <Text style={styles.name}>{label}</Text>
          <Text style={[styles.hint, { color: "#1a3d1a" }]}>
            {isIdle ? "à espera no jardim…" : "reagindo…"}
          </Text>
        </LinearGradient>
      </View>
    );
  }

  const { Video, ResizeMode } = av;

  return (
    <View style={[styles.wrap, { borderColor: "#5A9E62", backgroundColor: "#6BB36E" }]}>
      <View style={styles.stage}>
        {videoUri ? (
          <Video
            ref={videoRef}
            source={{ uri: videoUri }}
            style={[styles.video, !ready ? styles.videoHidden : null]}
            resizeMode={ResizeMode.COVER}
            isLooping={isIdle}
            isMuted={isIdle}
            shouldPlay
            useNativeControls={false}
            onReadyForDisplay={() => {
              setReady(true);
              void videoRef.current?.setPositionAsync?.(0);
              void videoRef.current?.playAsync?.();
            }}
            onPlaybackStatusUpdate={onStatus}
            onError={() => {
              setLoadError(true);
              setReady(false);
            }}
          />
        ) : null}
        {!ready ? (
          <View style={styles.fallback}>
            <MoodMonsterIllustration moodKey={key} size={100} />
          </View>
        ) : null}
        <View style={styles.caption}>
          <Text style={styles.name}>{label}</Text>
          <Text style={styles.liveHint}>{isIdle ? "● presente" : "● reagindo"}</Text>
        </View>
      </View>
    </View>
  );
}

export function requestMoodReact(nonce: number): MonsterPetPlayRequest {
  return { action: "mood-react", nonce };
}

export function requestGoalClip(
  goalKey: string,
  surprise: boolean | undefined,
  nonce: number,
  allGoalsBonus?: boolean
): MonsterPetPlayRequest {
  if (allGoalsBonus) return { action: "all-goals", nonce };
  return { action: clipActionForGoalKey(goalKey, surprise), nonce };
}

const styles = StyleSheet.create({
  wrap: {
    marginHorizontal: 16,
    marginBottom: 8,
    borderRadius: 16,
    borderWidth: 2,
    overflow: "hidden",
  },
  stage: {
    height: 220,
    backgroundColor: "#6BB36E",
    justifyContent: "flex-end",
  },
  video: {
    ...StyleSheet.absoluteFillObject,
  },
  videoHidden: { opacity: 0 },
  fallback: {
    ...StyleSheet.absoluteFillObject,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#6BB36E",
  },
  caption: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: "rgba(255,255,255,0.55)",
    alignItems: "center",
  },
  name: {
    fontSize: 16,
    fontWeight: "900",
    color: "#1a3d1a",
  },
  liveHint: {
    marginTop: 2,
    fontSize: 11,
    fontWeight: "700",
    color: "#2d5a2d",
  },
  hint: { fontSize: 11, fontWeight: "600", marginTop: 4 },
});
