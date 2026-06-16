import DateTimePicker, {
  type DateTimePickerEvent,
} from "@react-native-community/datetimepicker";
import React, { useMemo, useState } from "react";
import { Platform, Pressable, Text, View, type TextStyle, type ViewStyle } from "react-native";
import type { AppColors } from "@/theme/colors";
import {
  AGENDA_TIME_MINUTE_INTERVAL,
  combineDateAndTime,
  formatDateBr,
  formatDateFriendly,
  formatTimeHm,
} from "./agendaUtils";
import { agendaFormStyles as s } from "./agendaFormStyles";

type FieldStyle = ViewStyle | TextStyle;

type Props = {
  colors: AppColors;
  dateValue: string;
  timeValue: string;
  onDateChange: (value: string) => void;
  onTimeChange: (value: string) => void;
  dateInputStyle?: FieldStyle[];
  timeInputStyle?: FieldStyle[];
};

function PickerActions({
  colors,
  onCancel,
  onConfirm,
}: {
  colors: AppColors;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <View style={pickerStyles.actions}>
      <Pressable
        onPress={onCancel}
        hitSlop={8}
        accessibilityRole="button"
        accessibilityLabel="Cancelar"
      >
        <Text style={[pickerStyles.cancel, { color: colors.textMuted }]}>Cancelar</Text>
      </Pressable>
      <Pressable
        onPress={onConfirm}
        hitSlop={8}
        accessibilityRole="button"
        accessibilityLabel="Confirmar data ou hora"
      >
        <Text style={[pickerStyles.ok, { color: colors.primary }]}>OK</Text>
      </Pressable>
    </View>
  );
}

const pickerStyles = {
  sheet: {
    borderRadius: 12,
    borderWidth: 1,
    marginBottom: 8,
    overflow: "hidden" as const,
  },
  actions: {
    flexDirection: "row" as const,
    justifyContent: "flex-end" as const,
    alignItems: "center" as const,
    gap: 20,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  cancel: { fontSize: 16, fontWeight: "600" },
  ok: { fontSize: 16, fontWeight: "800" },
};

export function AgendaDateTimeFields({
  colors,
  dateValue,
  timeValue,
  onDateChange,
  onTimeChange,
  dateInputStyle,
  timeInputStyle,
}: Props) {
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showTimePicker, setShowTimePicker] = useState(false);
  const [draft, setDraft] = useState(() => new Date());

  const pickerValue = useMemo(
    () => combineDateAndTime(dateValue, timeValue),
    [dateValue, timeValue]
  );

  const fieldStyle = (extra?: FieldStyle[]): FieldStyle[] => [
    s.inviteInput,
    {
      color: colors.text,
      borderColor: colors.border,
      backgroundColor: colors.bgCard,
      justifyContent: "center" as const,
    },
    ...(extra ?? []),
  ];

  const openDate = () => {
    setShowTimePicker(false);
    setDraft(pickerValue);
    setShowDatePicker(true);
  };

  const openTime = () => {
    setShowDatePicker(false);
    setDraft(pickerValue);
    setShowTimePicker(true);
  };

  const onDatePickerChange = (event: DateTimePickerEvent, selected?: Date) => {
    if (Platform.OS === "android") {
      setShowDatePicker(false);
      if (event.type === "dismissed" || !selected) return;
      onDateChange(formatDateBr(selected));
      return;
    }
    if (selected) setDraft(selected);
  };

  const onTimePickerChange = (event: DateTimePickerEvent, selected?: Date) => {
    if (Platform.OS === "android") {
      setShowTimePicker(false);
      if (event.type === "dismissed" || !selected) return;
      onTimeChange(formatTimeHm(selected));
      return;
    }
    if (selected) setDraft(selected);
  };

  const confirmDate = () => {
    onDateChange(formatDateBr(draft));
    setShowDatePicker(false);
  };

  const confirmTime = () => {
    onTimeChange(formatTimeHm(draft));
    setShowTimePicker(false);
  };

  return (
    <>
      <View style={s.eventRowInputs}>
        <Pressable
          onPress={openDate}
          accessibilityRole="button"
          accessibilityLabel="Escolher data"
          style={fieldStyle([s.eventDateInput, ...(dateInputStyle ?? [])])}
        >
          <Text style={{ color: colors.text, fontSize: 15 }}>
            {dateValue ? formatDateFriendly(dateValue) : "Toque para escolher data"}
          </Text>
        </Pressable>
        <Pressable
          onPress={openTime}
          accessibilityRole="button"
          accessibilityLabel="Escolher hora"
          style={fieldStyle([s.eventTimeInput, ...(timeInputStyle ?? [])])}
        >
          <Text style={{ color: colors.text, fontSize: 15 }}>{timeValue || "Toque para escolher hora"}</Text>
        </Pressable>
      </View>

      {showDatePicker ? (
        <View
          style={[
            pickerStyles.sheet,
            { borderColor: colors.border, backgroundColor: colors.bgCard },
          ]}
        >
          <DateTimePicker
            value={draft}
            mode="date"
            display={Platform.OS === "ios" ? "spinner" : "default"}
            onChange={onDatePickerChange}
            locale="pt-BR"
          />
          {Platform.OS === "ios" ? (
            <PickerActions
              colors={colors}
              onCancel={() => setShowDatePicker(false)}
              onConfirm={confirmDate}
            />
          ) : null}
        </View>
      ) : null}

      {showTimePicker ? (
        <View
          style={[
            pickerStyles.sheet,
            { borderColor: colors.border, backgroundColor: colors.bgCard },
          ]}
        >
          <DateTimePicker
            value={draft}
            mode="time"
            is24Hour
            minuteInterval={AGENDA_TIME_MINUTE_INTERVAL}
            display={Platform.OS === "ios" ? "spinner" : "default"}
            onChange={onTimePickerChange}
            locale="pt-BR"
          />
          {Platform.OS === "ios" ? (
            <PickerActions
              colors={colors}
              onCancel={() => setShowTimePicker(false)}
              onConfirm={confirmTime}
            />
          ) : null}
        </View>
      ) : null}
    </>
  );
}

type TimeOnlyProps = {
  colors: AppColors;
  value: string;
  onChange: (value: string) => void;
  inputStyle?: FieldStyle[];
};

/** Campo de hora (hábitos semanais). */
export function AgendaTimeField({ colors, value, onChange, inputStyle }: TimeOnlyProps) {
  const [showTimePicker, setShowTimePicker] = useState(false);
  const [draft, setDraft] = useState(() => new Date());

  const pickerValue = useMemo(() => {
    const d = new Date();
    d.setHours(8, 0, 0, 0);
    const parts = value.match(/^(\d{1,2}):(\d{2})$/);
    if (parts) {
      d.setHours(Number(parts[1]), Number(parts[2]), 0, 0);
    }
    return d;
  }, [value]);

  const openTimePicker = () => {
    setDraft(pickerValue);
    setShowTimePicker(true);
  };

  const onTimePickerChange = (event: DateTimePickerEvent, selected?: Date) => {
    if (Platform.OS === "android") {
      setShowTimePicker(false);
      if (event.type === "dismissed" || !selected) return;
      onChange(formatTimeHm(selected));
      return;
    }
    if (selected) setDraft(selected);
  };

  return (
    <>
      <Pressable
        onPress={openTimePicker}
        accessibilityRole="button"
        accessibilityLabel="Escolher horário"
        style={[
          s.inviteInput,
          {
            color: colors.text,
            borderColor: colors.border,
            backgroundColor: colors.bg,
            justifyContent: "center",
          },
          ...(inputStyle ?? []),
        ]}
      >
        <Text style={{ color: colors.text, fontSize: 15 }}>{value || "Hora"}</Text>
      </Pressable>
      {showTimePicker ? (
        <View
          style={[
            pickerStyles.sheet,
            { borderColor: colors.border, backgroundColor: colors.bgCard },
          ]}
        >
          <DateTimePicker
            value={draft}
            mode="time"
            is24Hour
            minuteInterval={AGENDA_TIME_MINUTE_INTERVAL}
            display={Platform.OS === "ios" ? "spinner" : "default"}
            onChange={onTimePickerChange}
            locale="pt-BR"
          />
          {Platform.OS === "ios" ? (
            <PickerActions
              colors={colors}
              onCancel={() => setShowTimePicker(false)}
              onConfirm={() => {
                onChange(formatTimeHm(draft));
                setShowTimePicker(false);
              }}
            />
          ) : null}
        </View>
      ) : null}
    </>
  );
}
