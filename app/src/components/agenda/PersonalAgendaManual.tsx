import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  Text,
  TextInput,
  View,
} from "react-native";
import {
  createAgendaItem,
  createReminder,
  deleteAgendaItem,
  dismissReminder,
  localDateTimeToIso,
  recordStreakActivity,
} from "@/api/client";
import type {
  AgendaDraft,
  AgendaItem,
  Reminder,
  ShoppingListItem,
} from "@/api/types";
import { AgendaItemRow } from "@/components/AgendaItem";
import { ReminderItem } from "@/components/ReminderItem";
import type { AppColors } from "@/theme/colors";
import { AgendaDateTimeFields, AgendaTimeField } from "./AgendaDateTimeFields";
import { AgendaQuickPick } from "./AgendaQuickPick";
import { AgendaWeekdayChips } from "./AgendaWeekdayChips";
import { AgendaDraftsBanner } from "./AgendaDraftsBanner";
import { OrphanShoppingSection } from "./OrphanShoppingSection";
import { agendaFormStyles as s } from "./agendaFormStyles";
import {
  defaultScheduleSlot,
  defaultTimeHm,
  filterVisibleReminders,
} from "./agendaUtils";

type Props = {
  colors: AppColors;
  reminders: Reminder[];
  habits: AgendaItem[];
  agendaDrafts: AgendaDraft[];
  shoppingOrphans: ShoppingListItem[];
  onRefresh: () => Promise<void>;
  nightDumpNights?: number;
};

/**
 * Agenda pessoal 100% manual — não importa chat, voz nem AuthContext.
 * Alterações aqui não devem tocar em useVoiceChat / login.
 */
export function PersonalAgendaManual({
  colors,
  reminders,
  habits,
  agendaDrafts,
  shoppingOrphans,
  onRefresh,
  nightDumpNights = 0,
}: Props) {
  const initialSlot = defaultScheduleSlot();
  const [showPersonalForm, setShowPersonalForm] = useState(false);
  const [personalTitle, setPersonalTitle] = useState("");
  const [personalDate, setPersonalDate] = useState(initialSlot.date);
  const [personalTime, setPersonalTime] = useState(initialSlot.time);
  const [savingPersonal, setSavingPersonal] = useState(false);
  const [showHabitForm, setShowHabitForm] = useState(false);
  const [habitTitle, setHabitTitle] = useState("Academia");
  const [habitTime, setHabitTime] = useState(defaultTimeHm(8, 0));
  const [habitDays, setHabitDays] = useState("seg,ter,qua,qui,sex");
  const [savingHabit, setSavingHabit] = useState(false);
  const [habitDoneBusy, setHabitDoneBusy] = useState<string | null>(null);
  const [listTick, setListTick] = useState(0);

  const openPersonalForm = () => {
    const slot = defaultScheduleSlot();
    setPersonalDate(slot.date);
    setPersonalTime(slot.time);
    setPersonalTitle("");
    setShowPersonalForm(true);
  };

  const resetPersonalForm = () => {
    const slot = defaultScheduleSlot();
    setPersonalTitle("");
    setPersonalDate(slot.date);
    setPersonalTime(slot.time);
  };

  useEffect(() => {
    const id = setInterval(() => setListTick((t) => t + 1), 60_000);
    return () => clearInterval(id);
  }, []);

  const visibleReminders = useMemo(
    () => filterVisibleReminders(reminders),
    [reminders, listTick]
  );

  const inputStyle = [
    s.inviteInput,
    { color: colors.text, borderColor: colors.border, backgroundColor: colors.bg },
  ];

  const onAddPersonalReminder = async () => {
    const title = personalTitle.trim() || "Compromisso";
    const iso = localDateTimeToIso(personalDate.trim(), personalTime.trim());
    if (!iso) {
      Alert.alert("Data/hora", "Escolha data e hora e toque OK em cada uma.");
      return;
    }
    setSavingPersonal(true);
    try {
      await createReminder({ title, scheduled_at: iso, announce: title });
      setShowPersonalForm(false);
      resetPersonalForm();
      await onRefresh();
    } catch (e) {
      Alert.alert(
        "Erro",
        e instanceof Error ? e.message : "Não foi possível marcar o compromisso."
      );
    } finally {
      setSavingPersonal(false);
    }
  };

  const onAddHabit = async () => {
    const titulo = habitTitle.trim() || "Hábito";
    const horario = habitTime.trim();
    const dias = habitDays.trim();
    if (!/^\d{1,2}:\d{2}$/.test(horario)) {
      Alert.alert("Horário", "Use HH:MM (ex.: 08:00).");
      return;
    }
    if (!dias) {
      Alert.alert("Dias", "Toque nos dias da semana (ex.: seg–sex).");
      return;
    }
    setSavingHabit(true);
    try {
      await createAgendaItem({ titulo, horario, dias_da_semana: dias });
      setShowHabitForm(false);
      setHabitTitle("Academia");
      setHabitTime(defaultTimeHm(8, 0));
      setHabitDays("seg,ter,qua,qui,sex");
      await onRefresh();
    } catch (e) {
      Alert.alert(
        "Erro",
        e instanceof Error ? e.message : "Não foi possível criar o hábito."
      );
    } finally {
      setSavingHabit(false);
    }
  };

  const onDismissReminder = (reminderId: string) => {
    const item = visibleReminders.find((r) => String(r.id) === reminderId);
    const title = (item?.title || "Compromisso").trim();
    Alert.alert("Apagar", `Apagar «${title}» da agenda?`, [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Apagar",
        style: "destructive",
        onPress: async () => {
          try {
            await dismissReminder(reminderId);
            await onRefresh();
          } catch (e) {
            Alert.alert(
              "Erro",
              e instanceof Error ? e.message : "Não foi possível apagar o compromisso."
            );
          }
        },
      },
    ]);
  };

  const onDeleteHabit = (agendaId: string) => {
    const item = habits.find((a) => String(a.id) === agendaId);
    const title = (item?.titulo || "Hábito").trim();
    Alert.alert("Apagar", `Apagar «${title}» da agenda?`, [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Apagar",
        style: "destructive",
        onPress: async () => {
          try {
            await deleteAgendaItem(agendaId);
            await onRefresh();
          } catch (e) {
            Alert.alert(
              "Erro",
              e instanceof Error ? e.message : "Não foi possível apagar o hábito."
            );
          }
        },
      },
    ]);
  };

  const onHabitDoneToday = async (agendaId: string) => {
    setHabitDoneBusy(agendaId);
    try {
      await recordStreakActivity("habit");
      Alert.alert("Ofensiva", "Hábito marcado — sua sequência continua! 🔥");
      await onRefresh();
    } catch (e) {
      Alert.alert(
        "Erro",
        e instanceof Error ? e.message : "Não foi possível registar o hábito."
      );
    } finally {
      setHabitDoneBusy(null);
    }
  };

  return (
    <>
      <AgendaDraftsBanner
        colors={colors}
        drafts={agendaDrafts}
        onRefresh={onRefresh}
        familyOnly={false}
        nightDumpNights={nightDumpNights}
      />
      <OrphanShoppingSection colors={colors} items={shoppingOrphans} onRefresh={onRefresh} />
      <Text style={[s.section, { color: colors.textMuted }]}>Compromissos</Text>
      <Pressable
        onPress={() => (showPersonalForm ? setShowPersonalForm(false) : openPersonalForm())}
        style={({ pressed }) => [
          s.addBtn,
          {
            borderColor: colors.primary,
            backgroundColor: showPersonalForm ? colors.primaryTint : colors.bgCard,
            opacity: pressed ? 0.88 : 1,
          },
        ]}
      >
        <Text style={[s.addBtnText, { color: colors.primary }]}>
          {showPersonalForm ? "Fechar formulário" : "+ Novo compromisso"}
        </Text>
      </Pressable>
      {showPersonalForm ? (
        <View style={[s.formBox, { borderColor: colors.border, backgroundColor: colors.bgCard }]}>
          <TextInput
            value={personalTitle}
            onChangeText={setPersonalTitle}
            placeholder="O que é? (ex.: consulta, reunião)"
            placeholderTextColor={colors.textMuted}
            style={inputStyle}
            autoFocus
          />
          <AgendaQuickPick
            colors={colors}
            dateValue={personalDate}
            onDatePick={setPersonalDate}
            titleValue={personalTitle}
            onTitlePick={setPersonalTitle}
          />
          <AgendaDateTimeFields
            colors={colors}
            dateValue={personalDate}
            timeValue={personalTime}
            onDateChange={setPersonalDate}
            onTimeChange={setPersonalTime}
            dateInputStyle={[{ backgroundColor: colors.bg }]}
            timeInputStyle={[{ backgroundColor: colors.bg }]}
          />
          <Pressable
            onPress={onAddPersonalReminder}
            disabled={savingPersonal}
            style={[s.inviteBtn, { backgroundColor: colors.primary }]}
          >
            {savingPersonal ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={s.inviteBtnText}>Marcar compromisso</Text>
            )}
          </Pressable>
        </View>
      ) : null}
      {visibleReminders.length === 0 ? (
        <Text style={[s.muted, { color: colors.textMuted }]}>
          Nenhum compromisso. Toque em «+ Novo compromisso» — leva menos de 10 segundos.
        </Text>
      ) : (
        visibleReminders.map((r) => {
          const rid = String(r.id);
          return (
            <ReminderItem
              key={rid}
              item={r}
              colors={colors}
              onDismiss={onDismissReminder}
              onShoppingChange={onRefresh}
            />
          );
        })
      )}

      <Text style={[s.section, { color: colors.textMuted }]}>Hábitos semanais</Text>
      <Pressable
        onPress={() => setShowHabitForm((v) => !v)}
        style={({ pressed }) => [
          s.addBtn,
          {
            borderColor: colors.primary,
            backgroundColor: showHabitForm ? colors.primaryTint : colors.bgCard,
            opacity: pressed ? 0.88 : 1,
          },
        ]}
      >
        <Text style={[s.addBtnText, { color: colors.primary }]}>
          {showHabitForm ? "Fechar formulário" : "+ Novo hábito"}
        </Text>
      </Pressable>
      {showHabitForm ? (
        <View style={[s.formBox, { borderColor: colors.border, backgroundColor: colors.bgCard }]}>
          <Text style={[s.formLabel, { color: colors.textMuted }]}>
            Rotina semanal (ex.: academia seg–sex às 8h)
          </Text>
          <TextInput
            value={habitTitle}
            onChangeText={setHabitTitle}
            placeholder="Nome (ex.: Academia)"
            placeholderTextColor={colors.textMuted}
            style={inputStyle}
          />
          <AgendaTimeField colors={colors} value={habitTime} onChange={setHabitTime} inputStyle={inputStyle} />
          <AgendaWeekdayChips colors={colors} value={habitDays} onChange={setHabitDays} />
          <Pressable
            onPress={onAddHabit}
            disabled={savingHabit}
            style={[s.inviteBtn, { backgroundColor: colors.primary }]}
          >
            {savingHabit ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={s.inviteBtnText}>Adicionar hábito</Text>
            )}
          </Pressable>
        </View>
      ) : null}
      {habits.length === 0 ? (
        <Text style={[s.muted, { color: colors.textMuted }]}>
          Nenhum hábito. Toque em «+ Novo hábito» e escolha os dias da semana.
        </Text>
      ) : (
        habits.map((a) => {
          const aid = String(a.id);
          return (
            <AgendaItemRow
              key={aid}
              item={a}
              colors={colors}
              onDelete={onDeleteHabit}
              onDoneToday={() => void onHabitDoneToday(aid)}
              doneTodayBusy={habitDoneBusy === aid}
            />
          );
        })
      )}
    </>
  );
}
