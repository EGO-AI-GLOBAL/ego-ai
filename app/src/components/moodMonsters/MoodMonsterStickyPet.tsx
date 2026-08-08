import { Asset } from "expo-asset";
import { LinearGradient } from "expo-linear-gradient";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";
import type { DailyCarePet } from "@/api/types";
import {
  clipActionForGoalKey,
  monsterClipModule,
  type MonsterClipAction,
} from "@/constants/monsterClipAssets";
import { moodKeyOrDefault, resolveMoodLabel } from "@/constants/moodMonsters";
import { petDisplayName, petStageStyle } from "@/constants/moodPetStages";
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
  /** Nível/fase do monstrinho — evolução visível no palco. */
  pet?: DailyCarePet | null;
  /** Toque na legenda → baptizar / mudar nome. */
  onPressName?: () => void;
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
  pet,
  onPressName,
}: Props) {
  const av = useMemo(() => loadExpoAv(), []);
  const key = moodKeyOrDefault(moodKey);
  const label = resolveMoodLabel(moods, key);
  const stage = petStageStyle(pet?.stage_key);
  const displayName = petDisplayName(pet?.name, label);
  const hasName = Boolean((pet?.name || "").trim());
  const xpPct = Math.max(0, Math.min(100, pet?.progress_pct ?? 0));

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

  const caption = (
    <Pressable
      onPress={onPressName}
      disabled={!onPressName}
      style={[styles.caption, { backgroundColor: stage.aura }]}
    >
      <View style={styles.captionRow}>
        <Text style={[styles.name, { color: stage.badgeText }]} numberOfLines={1}>
          {displayName}
        </Text>
        {onPressName ? (
          <Text style={[styles.rename, { color: stage.badgeText }]}>
            {hasName ? "✏️" : "dar nome"}
          </Text>
        ) : null}
      </View>

      {pet ? (
        <>
          <View style={[styles.badge, { backgroundColor: stage.badgeBg }]}>
            <Text style={[styles.badgeText, { color: stage.badgeText }]}>
              {pet.stage_emoji} Nível {pet.level} · {pet.stage_label}
            </Text>
          </View>
          <View style={styles.xpBg}>
            <View style={[styles.xpFill, { width: `${xpPct}%`, backgroundColor: stage.border }]} />
          </View>
        </>
      ) : (
        <Text style={[styles.liveHint, { color: stage.badgeText }]}>
          {isIdle ? "● presente" : "● reagindo"}
        </Text>
      )}
    </Pressable>
  );

  if (!av?.Video || loadError || Platform.OS === "web") {
    return (
      <View style={[styles.wrap, { borderColor: stage.border, backgroundColor: "#6BB36E" }]}>
        <LinearGradient colors={[...gardenGreen]} style={styles.stage}>
          <MoodMonsterIllustration moodKey={key} size={128} celebrate={!isIdle} />
          {caption}
        </LinearGradient>
      </View>
    );
  }

  const { Video, ResizeMode } = av;

  return (
    <View style={[styles.wrap, { borderColor: stage.border, backgroundColor: "#6BB36E" }]}>
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
        {caption}
      </View>
    </View>
  );
}

export function requestMoodReact(nonce: number): MonsterPetPlayRequest {
  return { action: "mood-react", nonce };
}

export function requestGardenClip(
  action: MonsterClipAction,
  nonce: number
): MonsterPetPlayRequest {
  return { action, nonce };
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
    alignItems: "center",
  },
  captionRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  name: {
    fontSize: 16,
    fontWeight: "900",
    maxWidth: 200,
  },
  rename: {
    fontSize: 11,
    fontWeight: "800",
    opacity: 0.75,
  },
  badge: {
    marginTop: 4,
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 999,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: "800",
  },
  xpBg: {
    marginTop: 6,
    height: 5,
    width: "70%",
    borderRadius: 999,
    backgroundColor: "rgba(0,0,0,0.16)",
    overflow: "hidden",
  },
  xpFill: {
    height: 5,
    borderRadius: 999,
  },
  liveHint: {
    marginTop: 2,
    fontSize: 11,
    fontWeight: "700",
  },
});
