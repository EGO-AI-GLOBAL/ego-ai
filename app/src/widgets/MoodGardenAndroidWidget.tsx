import React from "react";
import { FlexWidget, TextWidget } from "react-native-android-widget";
import type { MoodGardenWidgetSnapshot } from "@/storage/moodGardenWidgetSnapshot";

type Props = {
  snapshot: MoodGardenWidgetSnapshot;
};

export function MoodGardenAndroidWidget({ snapshot }: Props) {
  const bg = snapshot.atRisk ? "#FFF7ED" : "#ECFDF5";
  const border = snapshot.atRisk ? "#F59E0B" : "#86EFAC";

  return (
    <FlexWidget
      style={{
        height: "match_parent",
        width: "match_parent",
        backgroundColor: bg,
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
          text={snapshot.title}
          style={{ fontSize: 14, fontWeight: "700", color: "#14532D" }}
        />
        <TextWidget
          text={snapshot.subtitle}
          maxLines={2}
          style={{ fontSize: 12, color: "#166534", marginTop: 4 }}
        />
        {snapshot.goalsLine ? (
          <TextWidget
            text={snapshot.goalsLine}
            style={{ fontSize: 11, color: "#15803D", marginTop: 6, fontWeight: "600" }}
          />
        ) : null}
        {snapshot.atRisk ? (
          <TextWidget
            text="Sequência em risco"
            style={{ fontSize: 11, color: "#B45309", marginTop: 4, fontWeight: "700" }}
          />
        ) : null}
      </FlexWidget>
      <TextWidget text={snapshot.emoji} style={{ fontSize: 36, marginLeft: 8 }} />
    </FlexWidget>
  );
}
