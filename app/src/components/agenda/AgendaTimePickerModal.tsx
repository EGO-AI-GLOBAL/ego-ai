import DateTimePicker, {
  type DateTimePickerEvent,
} from "@react-native-community/datetimepicker";
import React from "react";
import { Modal, Platform, Pressable, StyleSheet, Text, View } from "react-native";
import type { AppColors } from "@/theme/colors";
import { AGENDA_TIME_MINUTE_INTERVAL, snapMinute } from "./agendaUtils";

type Props = {
  visible: boolean;
  value: Date;
  colors: AppColors;
  onCancel: () => void;
  onConfirm: (value: Date) => void;
};

function snapTime(date: Date): Date {
  const snapped = new Date(date);
  snapped.setMinutes(
    snapMinute(snapped.getMinutes(), AGENDA_TIME_MINUTE_INTERVAL),
    0,
    0
  );
  return snapped;
}

/**
 * Hora na agenda.
 * Android: diálogo nativo do sistema (fora do ScrollView — funciona).
 * iOS: folha com spinner + Cancelar/OK.
 */
export function AgendaTimePickerModal({
  visible,
  value,
  colors,
  onCancel,
  onConfirm,
}: Props) {
  const [draft, setDraft] = React.useState(value);

  React.useEffect(() => {
    if (visible) setDraft(value);
  }, [visible, value]);

  const onAndroidChange = (event: DateTimePickerEvent, selected?: Date) => {
    if (event.type !== "set" || !selected) {
      onCancel();
      return;
    }
    onConfirm(snapTime(selected));
  };

  if (Platform.OS === "android") {
    if (!visible) return null;
    return (
      <DateTimePicker
        value={draft}
        mode="time"
        is24Hour
        display="default"
        onChange={onAndroidChange}
      />
    );
  }

  const onIosChange = (_event: DateTimePickerEvent, selected?: Date) => {
    if (selected) setDraft(selected);
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onCancel}>
      <Pressable style={styles.backdrop} onPress={onCancel}>
        <Pressable
          style={[styles.sheet, { backgroundColor: colors.bgCard, borderColor: colors.border }]}
          onPress={(e) => e.stopPropagation()}
        >
          <DateTimePicker
            value={draft}
            mode="time"
            display="spinner"
            is24Hour
            minuteInterval={AGENDA_TIME_MINUTE_INTERVAL}
            onChange={onIosChange}
            locale="pt-BR"
            textColor={colors.text}
          />
          <View style={styles.actions}>
            <Pressable onPress={onCancel} hitSlop={8}>
              <Text style={[styles.cancel, { color: colors.textMuted }]}>Cancelar</Text>
            </Pressable>
            <Pressable onPress={() => onConfirm(snapTime(draft))} hitSlop={8}>
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
    overflow: "hidden",
  },
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
