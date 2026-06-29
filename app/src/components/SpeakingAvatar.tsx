import { Asset } from "expo-asset";
import React, { createElement, useCallback, useEffect, useRef, useState } from "react";
import {
  Animated,
  Image,
  Platform,
  StyleSheet,
  Text,
  View,
  type ImageStyle,
  type StyleProp,
} from "react-native";
import {
  avatarImageSource,
  avatarSpeakingVideoSource,
  isMaleAvatar,
} from "@/constants/personas";
import { findAvatarInCatalog } from "@/constants/avatarCatalog";
import { useColors } from "@/theme/ThemeContext";

type Props = {
  avatarId?: string;
  subtitle?: string;
  isSpeaking?: boolean;
  isListening?: boolean;
  isThinking?: boolean;
  compact?: boolean;
  /** Oculta o nome sob o avatar (ex.: chat com seletor de assistente). */
  hideLabel?: boolean;
};

type WebVideoProps = {
  uri: string;
  active: boolean;
  style: StyleProp<ImageStyle>;
  onReady?: () => void;
};

function WebAvatarVideo({ uri, active, style, onReady }: WebVideoProps) {
  const ref = useRef<HTMLVideoElement | null>(null);
  const wasActiveRef = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (active) {
      if (!wasActiveRef.current) {
        el.currentTime = 0;
      }
      void el.play().catch(() => undefined);
      wasActiveRef.current = true;
      return;
    }
    el.pause();
    el.currentTime = 0;
    wasActiveRef.current = false;
  }, [active, uri]);

  const flat = StyleSheet.flatten(style) as Record<string, unknown>;

  return createElement("video", {
    ref,
    src: uri,
    muted: true,
    loop: true,
    playsInline: true,
    onLoadedData: onReady,
    style: {
      ...flat,
      objectFit: "cover",
    },
  });
}

function NativeSpeakingVideo({
  avatarId,
  speaking,
}: {
  avatarId: string;
  speaking: boolean;
}) {
  const { Audio, Video, ResizeMode } = require("expo-av") as typeof import("expo-av");
  const videoRef = useRef<InstanceType<typeof Video>>(null);
  const wasSpeakingRef = useRef(false);
  const [videoUri, setVideoUri] = useState<string | null>(null);
  const [videoReady, setVideoReady] = useState(false);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    void Audio.setAudioModeAsync({
      allowsRecordingIOS: true,
      playsInSilentModeIOS: true,
      shouldDuckAndroid: true,
      playThroughEarpieceAndroid: false,
    }).catch(() => undefined);
  }, [Audio]);

  useEffect(() => {
    let cancelled = false;
    setVideoUri(null);
    setVideoReady(false);
    setLoadError(false);

    void (async () => {
      try {
        const mod = avatarSpeakingVideoSource(avatarId);
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
  }, [avatarId]);

  const syncPlayback = useCallback(async (play: boolean, resetPosition: boolean) => {
    const player = videoRef.current;
    if (!player) return;
    try {
      if (play) {
        if (resetPosition) {
          await player.setPositionAsync(0);
        }
        await player.playAsync();
      } else {
        await player.pauseAsync();
        await player.setPositionAsync(0);
      }
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    if (!videoUri || loadError) return;
    if (speaking && videoReady) {
      const reset = !wasSpeakingRef.current;
      wasSpeakingRef.current = true;
      void syncPlayback(true, reset);
      return;
    }
    if (!speaking) {
      wasSpeakingRef.current = false;
      void syncPlayback(false, true);
    }
  }, [speaking, videoReady, videoUri, loadError, syncPlayback]);

  const showVideo = speaking && Boolean(videoUri) && videoReady && !loadError;

  const onVideoReady = useCallback(() => {
    setVideoReady(true);
    if (speaking) {
      const reset = !wasSpeakingRef.current;
      wasSpeakingRef.current = true;
      void syncPlayback(true, reset);
    }
  }, [speaking, syncPlayback]);

  return (
    <>
      {videoUri && !loadError ? (
        <Video
          ref={videoRef}
          source={{ uri: videoUri }}
          style={[
            styles.media,
            styles.overlay,
            showVideo ? styles.videoOnTop : styles.videoHidden,
          ]}
          resizeMode={ResizeMode.COVER}
          isLooping
          isMuted
          shouldPlay={showVideo}
          useNativeControls={false}
          onReadyForDisplay={onVideoReady}
          onError={() => {
            setLoadError(true);
            setVideoReady(false);
          }}
        />
      ) : null}
      <Image
        source={avatarImageSource(avatarId)}
        style={[
          styles.media,
          styles.overlay,
          showVideo ? styles.photoHidden : styles.photoOnTop,
        ]}
        resizeMode="cover"
      />
    </>
  );
}

export function SpeakingAvatar({
  avatarId = "f1",
  subtitle,
  isSpeaking,
  isListening,
  isThinking,
  compact,
  hideLabel,
}: Props) {
  const colors = useColors();
  const speaking = Boolean(isSpeaking);
  const listening = Boolean(isListening);
  const thinking = Boolean(isThinking);
  const pulse = useRef(new Animated.Value(1)).current;
  const speakRing = useRef(new Animated.Value(0)).current;
  const aid = (avatarId || "f1").toLowerCase();
  const name =
    findAvatarInCatalog(aid)?.shortName ?? (isMaleAvatar(aid) ? "Leo" : "Luna");
  const [videoUri, setVideoUri] = useState<string | null>(null);
  const [videoReady, setVideoReady] = useState(false);

  useEffect(() => {
    if (!speaking) {
      speakRing.setValue(0);
      return;
    }
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(speakRing, {
          toValue: 1,
          duration: 700,
          useNativeDriver: true,
        }),
        Animated.timing(speakRing, {
          toValue: 0,
          duration: 700,
          useNativeDriver: true,
        }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [speaking, speakRing]);

  const ringOpacity = speakRing.interpolate({
    inputRange: [0, 1],
    outputRange: [0.35, 0.85],
  });
  const ringScale = speakRing.interpolate({
    inputRange: [0, 1],
    outputRange: [1, 1.06],
  });

  useEffect(() => {
    if (!listening && !thinking) {
      pulse.setValue(1);
      return;
    }
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1.04,
          duration: listening ? 700 : 520,
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 1,
          duration: listening ? 700 : 520,
          useNativeDriver: true,
        }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [listening, thinking, pulse]);

  useEffect(() => {
    let cancelled = false;
    setVideoUri(null);
    setVideoReady(false);

    void (async () => {
      try {
        const asset = Asset.fromModule(avatarSpeakingVideoSource(aid));
        await asset.downloadAsync();
        if (!cancelled) {
          setVideoUri(asset.localUri || asset.uri);
        }
      } catch {
        if (!cancelled) setVideoUri(null);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [aid]);

  const statusLabel = thinking
    ? `${name} está pensando…`
    : listening
      ? `${name} está ouvindo…`
      : speaking
        ? `${name} está falando…`
        : null;
  const showVideo = speaking && Boolean(videoUri) && videoReady;
  const frameBorderColor =
    thinking || listening || speaking ? colors.primarySoft : colors.border;

  return (
    <View style={[styles.wrap, compact && styles.wrapCompact]}>
      {speaking ? (
        <Animated.View
          style={[
            styles.speakRing,
            compact && styles.speakRingCompact,
            {
              borderColor: colors.glowCyan,
              opacity: ringOpacity,
              transform: [{ scale: ringScale }],
            },
          ]}
        />
      ) : null}
      <Animated.View
        style={[
          styles.frame,
          compact && styles.frameCompact,
          {
            backgroundColor: colors.bgCard,
            borderWidth: thinking || listening || speaking ? 2 : StyleSheet.hairlineWidth,
            borderColor: frameBorderColor,
            transform: [{ scale: pulse }],
          },
        ]}
      >
        {Platform.OS === "web" ? (
          <>
            {videoUri ? (
              <View
                style={[
                  styles.media,
                  styles.overlay,
                  showVideo ? styles.videoOnTop : styles.videoHidden,
                ]}
              >
                <WebAvatarVideo
                  uri={videoUri}
                  active={speaking}
                  style={styles.media}
                  onReady={() => setVideoReady(true)}
                />
              </View>
            ) : null}
            <Image
              source={avatarImageSource(aid)}
              style={[
                styles.media,
                styles.overlay,
                showVideo ? styles.photoHidden : styles.photoOnTop,
              ]}
              resizeMode="cover"
            />
          </>
        ) : (
          <NativeSpeakingVideo avatarId={aid} speaking={speaking} />
        )}
      </Animated.View>
      {statusLabel ? (
        <Text style={[styles.status, { color: colors.primary }]}>{statusLabel}</Text>
      ) : hideLabel ? null : (
        <Text style={[styles.name, { color: colors.textMuted }]}>{name}</Text>
      )}
      {subtitle ? (
        <Text style={[styles.sub, { color: colors.textMuted }]}>{subtitle}</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: "center", marginBottom: 20 },
  wrapCompact: { marginBottom: 8 },
  speakRing: {
    position: "absolute",
    width: 236,
    height: 296,
    borderRadius: 28,
    borderWidth: 3,
    top: -8,
  },
  speakRingCompact: {
    width: 164,
    height: 202,
    borderRadius: 22,
    top: -6,
  },
  frame: {
    width: 220,
    height: 280,
    borderRadius: 24,
    overflow: "hidden",
  },
  frameCompact: {
    width: 148,
    height: 186,
    borderRadius: 18,
  },
  media: {
    width: "100%",
    height: "100%",
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
  },
  photoOnTop: {
    opacity: 1,
    zIndex: 2,
  },
  photoHidden: {
    opacity: 0,
    zIndex: 0,
  },
  videoOnTop: {
    opacity: 1,
    zIndex: 2,
  },
  videoHidden: {
    opacity: 0,
    zIndex: 0,
  },
  status: { marginTop: 12, fontWeight: "600", fontSize: 13 },
  name: { marginTop: 12, fontSize: 13, fontWeight: "600" },
  sub: { marginTop: 4, fontSize: 15, textAlign: "center", lineHeight: 20, paddingHorizontal: 8 },
});
