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

  const onDatePickerChange = (event: DateTimePickerEvent, selected?: Date) => {
    if (Platform.OS === "android") setShowDatePicker(false);
    if (event.type === "dismissed" || !selected) return;
    onDateChange(formatDateBr(selected));
  };

  const onTimePickerChange = (event: DateTimePickerEvent, selected?: Date) => {
    if (Platform.OS === "android") setShowTimePicker(false);
    if (event.type === "dismissed" || !selected) return;
    onTimeChange(formatTimeHm(selected));
  };

  return (
    <>
      <View style={s.eventRowInputs}>
        <Pressable
          onPress={() => setShowDatePicker(true)}
          accessibilityRole="button"
          accessibilityLabel="Escolher data no calendário"
          style={fieldStyle([s.eventDateInput, ...(dateInputStyle ?? [])])}
        >
          <Text style={{ color: colors.text, fontSize: 15 }}>{dateValue || "DD/MM/AAAA"}</Text>
        </Pressable>
        <Pressable
          onPress={() => setShowTimePicker(true)}
          accessibilityRole="button"
          accessibilityLabel="Escolher hora"
          style={fieldStyle([s.eventTimeInput, ...(timeInputStyle ?? [])])}
        >
          <Text style={{ color: colors.text, fontSize: 15 }}>{timeValue || "HH:MM"}</Text>
        </Pressable>
      </View>
      <Text style={{ color: colors.textMuted, fontSize: 11, marginTop: -4, marginBottom: 4 }}>
        Toque na data ou hora para abrir o calendário (intervalos de{" "}
        {AGENDA_TIME_MINUTE_INTERVAL} min).
      </Text>
      {showDatePicker ? (
        <DateTimePicker
          value={pickerValue}
          mode="date"
          display={Platform.OS === "ios" ? "spinner" : "default"}
          onChange={onDatePickerChange}
        />
      ) : null}
      {showTimePicker ? (
        <DateTimePicker
          value={pickerValue}
          mode="time"
          is24Hour
          minuteInterval={AGENDA_TIME_MINUTE_INTERVAL}
          display={Platform.OS === "ios" ? "spinner" : "default"}
          onChange={onTimePickerChange}
        />
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
  const pickerValue = useMemo(() => {
    const d = new Date();
    d.setHours(8, 0, 0, 0);
    const parts = value.match(/^(\d{1,2}):(\d{2})$/);
    if (parts) {
      d.setHours(Number(parts[1]), Number(parts[2]), 0, 0);
    }
    return d;
  }, [value]);

  const onTimePickerChange = (event: DateTimePickerEvent, selected?: Date) => {
    if (Platform.OS === "android") setShowTimePicker(false);
    if (event.type === "dismissed" || !selected) return;
    onChange(formatTimeHm(selected));
  };

  return (
    <>
      <Pressable
        onPress={() => setShowTimePicker(true)}
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
        <Text style={{ color: colors.text, fontSize: 15 }}>{value || "HH:MM"}</Text>
      </Pressable>
      {showTimePicker ? (
        <DateTimePicker
          value={pickerValue}
          mode="time"
          is24Hour
          minuteInterval={AGENDA_TIME_MINUTE_INTERVAL}
          display={Platform.OS === "ios" ? "spinner" : "default"}
          onChange={onTimePickerChange}
        />
      ) : null}
    </>
  );
}
