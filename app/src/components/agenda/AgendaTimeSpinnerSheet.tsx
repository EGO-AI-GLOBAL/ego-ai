import React, { useEffect, useRef, useState } from "react";
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import type { AppColors } from "@/theme/colors";
import { AGENDA_TIME_MINUTE_INTERVAL, snapMinute } from "./agendaUtils";

const WHEEL_ITEM_H = 44;
const HOURS = Array.from({ length: 24 }, (_, i) => i);
const MINUTES = [0, 30];

type Props = {
  visible: boolean;
  value: Date;
  colors: AppColors;
  onCancel: () => void;
  onConfirm: (date: Date) => void;
};

function WheelColumn({
  items,
  selected,
  onSelect,
  format,
  colors,
}: {
  items: number[];
  selected: number;
  onSelect: (value: number) => void;
  format: (n: number) => string;
  colors: AppColors;
}) {
  const ref = useRef<ScrollView>(null);

  useEffect(() => {
    const idx = Math.max(0, items.indexOf(selected));
    ref.current?.scrollTo({ y: idx * WHEEL_ITEM_H, animated: false });
  }, [items, selected]);

  return (
    <ScrollView
      ref={ref}
      style={styles.wheel}
      snapToInterval={WHEEL_ITEM_H}
      decelerationRate="fast"
      showsVerticalScrollIndicator={false}
      nestedScrollEnabled
      onMomentumScrollEnd={(e) => {
        const idx = Math.round(e.nativeEvent.contentOffset.y / WHEEL_ITEM_H);
        const clamped = Math.min(Math.max(idx, 0), items.length - 1);
        onSelect(items[clamped] ?? items[0]);
      }}
      contentContainerStyle={styles.wheelPad}
    >
      {items.map((item) => {
        const active = item === selected;
        return (
          <View key={item} style={styles.wheelItem}>
            <Text
              style={[
                styles.wheelText,
                { color: active ? colors.text : colors.textMuted },
                active && styles.wheelTextActive,
              ]}
            >
              {format(item)}
            </Text>
          </View>
        );
      })}
    </ScrollView>
  );
}

/** Android: roda hora/minuto igual iOS (só :00 e :30). minuteInterval não existe no TimePicker Android. */
export function AgendaTimeSpinnerSheet({
  visible,
  value,
  colors,
  onCancel,
  onConfirm,
}: Props) {
  const [hour, setHour] = useState(value.getHours());
  const [minute, setMinute] = useState(
    snapMinute(value.getMinutes(), AGENDA_TIME_MINUTE_INTERVAL)
  );

  useEffect(() => {
    if (!visible) return;
    setHour(value.getHours());
    setMinute(snapMinute(value.getMinutes(), AGENDA_TIME_MINUTE_INTERVAL));
  }, [visible, value]);

  const confirm = () => {
    const next = new Date(value);
    next.setHours(hour, minute, 0, 0);
    onConfirm(next);
  };

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onCancel}>
      <Pressable style={styles.backdrop} onPress={onCancel}>
        <Pressable
          style={[styles.sheet, { backgroundColor: colors.bgCard, borderColor: colors.border }]}
          onPress={(e) => e.stopPropagation()}
        >
          <View style={styles.wheelsRow}>
            <WheelColumn
              items={HOURS}
              selected={hour}
              onSelect={setHour}
              format={(h) => String(h).padStart(2, "0")}
              colors={colors}
            />
            <Text style={[styles.colon, { color: colors.text }]}>:</Text>
            <WheelColumn
              items={MINUTES}
              selected={minute}
              onSelect={setMinute}
              format={(m) => String(m).padStart(2, "0")}
              colors={colors}
            />
          </View>
          <View style={styles.actions}>
            <Pressable onPress={onCancel} hitSlop={8}>
              <Text style={[styles.cancel, { color: colors.textMuted }]}>Cancelar</Text>
            </Pressable>
            <Pressable onPress={confirm} hitSlop={8}>
              <Text style={[styles.ok, { color: colors.primary }]}>OK</Text>
            </Pressable>
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.45)",
    justifyContent: "flex-end",
  },
  sheet: {
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    borderWidth: StyleSheet.hairlineWidth,
    paddingBottom: 8,
  },
  wheelsRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 24,
    height: WHEEL_ITEM_H * 5,
  },
  wheel: { flex: 1, maxWidth: 88 },
  wheelPad: { paddingVertical: WHEEL_ITEM_H * 2 },
  wheelItem: {
    height: WHEEL_ITEM_H,
    justifyContent: "center",
    alignItems: "center",
  },
  wheelText: { fontSize: 22 },
  wheelTextActive: { fontWeight: "700", fontSize: 24 },
  colon: { fontSize: 24, fontWeight: "700", marginHorizontal: 4 },
  actions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
    gap: 20,
    paddingHorizontal: 18,
    paddingVertical: 12,
  },
  cancel: { fontSize: 16, fontWeight: "600" },
  ok: { fontSize: 16, fontWeight: "800" },
});
