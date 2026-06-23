import DateTimePicker, {
  type DateTimePickerEvent,
} from "@react-native-community/datetimepicker";
import React, { createContext, useCallback, useContext, useState } from "react";
import { Platform } from "react-native";
import { AGENDA_TIME_MINUTE_INTERVAL, snapMinute } from "./agendaUtils";

type PickRequest = {
  value: Date;
  onPick: (date: Date) => void;
};

const AgendaAndroidTimePickerContext = createContext<
  ((request: PickRequest) => void) | null
>(null);

/** Android: relógio nativo fora do ScrollView (ecrã agenda). */
export function useAgendaAndroidTimePicker(): (request: PickRequest) => void {
  const open = useContext(AgendaAndroidTimePickerContext);
  return open ?? (() => undefined);
}

export function AgendaAndroidTimeHost({ children }: { children: React.ReactNode }) {
  const [request, setRequest] = useState<PickRequest | null>(null);

  const openPicker = useCallback((req: PickRequest) => {
    if (Platform.OS !== "android") return;
    setRequest(req);
  }, []);

  const onChange = (event: DateTimePickerEvent, selected?: Date) => {
    const onPick = request?.onPick;
    setRequest(null);
    if (event.type !== "set" || !selected || !onPick) return;
    const snapped = new Date(selected);
    snapped.setMinutes(
      snapMinute(snapped.getMinutes(), AGENDA_TIME_MINUTE_INTERVAL),
      0,
      0
    );
    onPick(snapped);
  };

  return (
    <AgendaAndroidTimePickerContext.Provider value={openPicker}>
      {children}
      {Platform.OS === "android" && request ? (
        <DateTimePicker
          value={request.value}
          mode="time"
          is24Hour
          display="default"
          onChange={onChange}
        />
      ) : null}
    </AgendaAndroidTimePickerContext.Provider>
  );
}
