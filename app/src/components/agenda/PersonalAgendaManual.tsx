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
} from "@/api/client";
import type { AgendaItem, Reminder } from "@/api/types";
import { AgendaItemRow } from "@/components/AgendaItem";
import { ReminderItem } from "@/components/ReminderItem";
import type { AppColors } from "@/theme/colors";
import { AgendaDateTimeFields, AgendaTimeField } from "./AgendaDateTimeFields";
import { agendaFormStyles as s } from "./agendaFormStyles";
import { defaultDateBr, defaultTimeHm, filterVisibleReminders } from "./agendaUtils";

type Props = {
  colors: AppColors;
  reminders: Reminder[];
  habits: AgendaItem[];
  onRefresh: () => Promise<void>;
};

/**
 * Agenda pessoal 100% manual — não importa chat, voz nem AuthContext.
 * Alterações aqui não devem tocar em useVoiceChat / login.
 */
export function PersonalAgendaManual({ colors, reminders, habits, onRefresh }: Props) {
  const [showPersonalForm, setShowPersonalForm] = useState(false);
  const [personalTitle, setPersonalTitle] = useState("Compromisso");
  const [personalDate, setPersonalDate] = useState(defaultDateBr);
  const [personalTime, setPersonalTime] = useState(defaultTimeHm(10, 0));
  const [savingPersonal, setSavingPersonal] = useState(false);
  const [showHabitForm, setShowHabitForm] = useState(false);
  const [habitTitle, setHabitTitle] = useState("Academia");
  const [habitTime, setHabitTime] = useState(defaultTimeHm(8, 0));
  const [habitDays, setHabitDays] = useState("seg,ter,qua,qui,sex");
  const [savingHabit, setSavingHabit] = useState(false);
  const [listTick, setListTick] = useState(0);

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
      Alert.alert("Data/hora", "Toque na data e na hora para escolher no calendário.");
      return;
    }
    setSavingPersonal(true);
    try {
      await createReminder({ title, scheduled_at: iso, announce: title });
      setShowPersonalForm(false);
      setPersonalTitle("Compromisso");
      setPersonalDate(defaultDateBr());
      setPersonalTime(defaultTimeHm(10, 0));
      await onRefresh();
      Alert.alert("Marcado", `«${title}» foi adicionado à sua agenda pessoal.`);
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
      Alert.alert("Dias", "Indique os dias (ex.: seg,ter,qua,qui,sex).");
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
      Alert.alert("Hábito criado", `«${titulo}» foi adicionado à agenda semanal.`);
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

  return (
    <>
      <Text style={[s.section, { color: colors.textMuted }]}>Compromissos</Text>
      <Pressable
        onPress={() => setShowPersonalForm((v) => !v)}
        style={({ pressed }) => [
          s.addBtn,
          {
            borderColor: colors.primary,
            backgroundColor: showPersonalForm ? colors.primaryLight : colors.bgCard,
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
          <Text style={[s.formLabel, { color: colors.textMuted }]}>
            Marcar na agenda pessoal (sem usar o chat)
          </Text>
          <TextInput
            value={personalTitle}
            onChangeText={setPersonalTitle}
            placeholder="Título (ex.: Consulta)"
            placeholderTextColor={colors.textMuted}
            style={inputStyle}
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
              <Text style={s.inviteBtnText}>Marcar</Text>
            )}
          </Pressable>
        </View>
      ) : null}
      {visibleReminders.length === 0 ? (
        <Text style={[s.muted, { color: colors.textMuted }]}>
          Nenhum compromisso. Toque em «+ Novo compromisso» ou use o avatar no chat.
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
            backgroundColor: showHabitForm ? colors.primaryLight : colors.bgCard,
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
          <TextInput
            value={habitDays}
            onChangeText={setHabitDays}
            placeholder="Dias: seg,ter,qua,qui,sex"
            placeholderTextColor={colors.textMuted}
            autoCapitalize="none"
            style={inputStyle}
          />
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
          Nenhum hábito. Toque em «+ Novo hábito» ou use o avatar no chat.
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
            />
          );
        })
      )}
    </>
  );
}
