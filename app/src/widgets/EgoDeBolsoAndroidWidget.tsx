import React from "react";
import { FlexWidget, TextWidget } from "react-native-android-widget";
import type { EgoDeBolsoWidgetSnapshot } from "@/storage/egoDeBolsoWidgetSnapshot";

type Props = {
  snapshot: EgoDeBolsoWidgetSnapshot;
};

export function EgoDeBolsoAndroidWidget({ snapshot }: Props) {
  const border = snapshot.dayComplete ? "#22D3EE" : "#334155";

  return (
    <FlexWidget
      style={{
        height: "match_parent",
        width: "match_parent",
        backgroundColor: "#121C2C",
        borderRadius: 16,
        borderWidth: 2,
        borderColor: border,
        padding: 14,
        flexDirection: "row",
        alignItems: "center",
      }}
      clickAction="OPEN_APP"
    >
      <FlexWidget style={{ flex: 1, flexDirection: "column", justifyContent: "center" }}>
        <TextWidget
          text="EGO DE BOLSO"
          style={{ fontSize: 10, fontWeight: "700", color: "#22D3EE" }}
        />
        <TextWidget
          text={snapshot.title}
          maxLines={1}
          style={{ fontSize: 14, fontWeight: "700", color: "#FFFFFF", marginTop: 4 }}
        />
        <TextWidget
          text={snapshot.missionsLine}
          maxLines={2}
          style={{ fontSize: 12, color: "#B0B8CC", marginTop: 6 }}
        />
        {snapshot.weeklyLine ? (
          <TextWidget
            text={snapshot.weeklyLine}
            maxLines={1}
            style={{ fontSize: 11, color: "#8892A8", marginTop: 4 }}
          />
        ) : null}
      </FlexWidget>
      <TextWidget text={snapshot.emoji} style={{ fontSize: 36, marginLeft: 8 }} />
    </FlexWidget>
  );
}
