import { Asset } from "expo-asset";
import React, { useEffect, useMemo, useState } from "react";
import { Platform, StyleSheet, View } from "react-native";
import { calmaClipModule, type CalmaClipKey } from "@/constants/calmaClipAssets";

function loadExpoAv(): typeof import("expo-av") | null {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    return require("expo-av");
  } catch {
    return null;
  }
}

type Props = {
  clipKey: CalmaClipKey;
  playing: boolean;
  /** Sem som se modo discreto. */
  muted?: boolean;
  height?: number;
};

/** Vídeo curto (~7s) em loop durante a sessão Calma 1 min. */
export function CalmaClipPlayer({ clipKey, playing, muted = false, height = 168 }: Props) {
  const av = useMemo(() => loadExpoAv(), []);
  const [uri, setUri] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setUri(null);
    setError(false);
    void (async () => {
      try {
        const asset = Asset.fromModule(calmaClipModule(clipKey));
        await asset.downloadAsync();
        if (!cancelled) setUri(asset.localUri || asset.uri);
      } catch {
        if (!cancelled) setError(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [clipKey]);

  if (!av?.Video || error || Platform.OS === "web" || !uri || !playing) {
    return <View style={[styles.placeholder, { height }]} />;
  }

  const { Video, ResizeMode } = av;

  return (
    <View style={[styles.wrap, { height }]}>
      <Video
        source={{ uri }}
        style={styles.video}
        resizeMode={ResizeMode.COVER}
        isLooping
        isMuted={muted}
        shouldPlay={playing}
        useNativeControls={false}
        onError={() => setError(true)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    width: "100%",
    borderRadius: 14,
    overflow: "hidden",
    backgroundColor: "#2a2440",
    marginTop: 12,
  },
  video: { width: "100%", height: "100%" },
  placeholder: {
    width: "100%",
    borderRadius: 14,
    backgroundColor: "transparent",
    marginTop: 4,
  },
});
