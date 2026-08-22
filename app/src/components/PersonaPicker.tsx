import React, { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { savePersonaChoice, updatePersonaPreset } from "@/api/client";
import type { PlanTier } from "@/api/types";
import {
  AVATAR_CATALOG,
  AVATAR_CATEGORY_LABELS,
  avatarsByCategory,
  findAvatarInCatalog,
  type AvatarCatalogEntry,
  type AvatarCategory,
} from "@/constants/avatarCatalog";
import {
  PERSONA_PRESETS,
  avatarImageSource,
  presetFromPersona,
  type PersonaChoice,
  type PersonaPresetId,
} from "@/constants/personas";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/hooks/useDashboard";
import {
  markPersonaConfiguredLocal,
  saveLocalPersonaChoice,
} from "@/storage/personaPrefs";
import type { AppColors } from "@/theme/colors";
import { resolveUserId } from "@/utils/resolveUserId";

const CHAT_CATEGORIES: AvatarCategory[] = ["female", "male", "neutral"];

type Props = {
  colors: AppColors;
  persona: PersonaChoice;
  onPersonaChange: (persona: PersonaChoice) => void;
  onSaved?: (persona: PersonaChoice) => void | Promise<void>;
  variant?: "settings" | "onboarding" | "chat";
  onComplete?: () => void;
  /** Bloqueia troca (ex.: gravando voz) */
  disabled?: boolean;
  planTier?: PlanTier | string;
};

export function PersonaPicker({
  colors,
  persona,
  onPersonaChange,
  onSaved,
  variant = "settings",
  onComplete,
  disabled = false,
  planTier = "essential",
}: Props) {
  const { session } = useAuth();
  const { data } = useDashboard();
  const isOnboarding = variant === "onboarding";
  const isChat = variant === "chat";
  const isSettings = variant === "settings";
  const [expanded, setExpanded] = useState(false);
  const [picked, setPicked] = useState<PersonaPresetId | null>(null);
  const [localPersona, setLocalPersona] = useState<PersonaChoice>(persona);
  const lastSavedRef = useRef<PersonaChoice>(persona);

  useEffect(() => {
    setLocalPersona(persona);
    lastSavedRef.current = persona;
  }, [persona.avatar_id, persona.voice_id]);

  const activePreset = presetFromPersona(localPersona.avatar_id, localPersona.voice_id);
  const activeCatalog =
    findAvatarInCatalog(localPersona.avatar_id) ??
    (activePreset === "male" ? findAvatarInCatalog("m1") : findAvatarInCatalog("f1")) ??
    AVATAR_CATALOG[0];

  const active = isOnboarding ? picked : activePreset;
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [okMsg, setOkMsg] = useState<string | null>(null);

  const persistLocal = async (choice: PersonaChoice) => {
    const uid = resolveUserId(session, data.me?.user_id);
    if (!uid) return;
    await markPersonaConfiguredLocal(uid);
    await saveLocalPersonaChoice(uid, choice);
  };

  const persist = async (choice: PersonaChoice, preset: PersonaPresetId) => {
    const isLeoLuna =
      (choice.avatar_id === "f1" && choice.voice_id === "vf1") ||
      (choice.avatar_id === "m1" && choice.voice_id === "vm1");
    // preset male/female só para Luna/Leo; catálogo (Hana, Sara, …) sempre por avatar_id.
    if (!isLeoLuna) {
      return await savePersonaChoice(choice);
    }
    if (preset === "male" || preset === "female") {
      try {
        return await updatePersonaPreset(preset);
      } catch {
        return await savePersonaChoice(choice);
      }
    }
    return await savePersonaChoice(choice);
  };

  const selectPreset = async (preset: PersonaPresetId) => {
    if (busyId || disabled) return;
    if (!isOnboarding && active === preset) return;

    const choice = PERSONA_PRESETS.find((p) => p.id === preset);
    if (!choice) return;

    const previous = { ...lastSavedRef.current };
    const next = { avatar_id: choice.avatar_id, voice_id: choice.voice_id };

    setError(null);
    setOkMsg(null);
    setBusyId(preset);
    if (isOnboarding) setPicked(preset);

    setLocalPersona(next);
    onPersonaChange(next);

    try {
      const saved = await persist(next, preset);
      const confirmed = { avatar_id: saved.avatar_id, voice_id: saved.voice_id };
      lastSavedRef.current = confirmed;
      setLocalPersona(confirmed);
      onPersonaChange(confirmed);

      await persistLocal(confirmed);
      if (isOnboarding) {
        await onSaved?.(confirmed);
        await onComplete?.();
        return;
      }
      setOkMsg(
        preset === "male"
          ? "Leo ativo · voz masculina."
          : "Luna ativa · voz feminina."
      );
      await onSaved?.(confirmed);
    } catch (e) {
      if (isOnboarding) {
        await persistLocal(next);
        await onSaved?.(next);
        await onComplete?.();
        return;
      }
      setLocalPersona(previous);
      onPersonaChange(previous);
      const msg = e instanceof Error ? e.message : "Não foi possível trocar.";
      setError(msg);
      if (isOnboarding) setPicked(null);
    } finally {
      setBusyId(null);
    }
  };

  const selectCatalogEntry = async (entry: AvatarCatalogEntry) => {
    if (busyId || disabled) return;
    if (localPersona.avatar_id === entry.avatar_id) {
      if (isChat) setExpanded(false);
      return;
    }

    const previous = { ...lastSavedRef.current };
    const next = { avatar_id: entry.avatar_id, voice_id: entry.voice_id };
    const preset = presetFromPersona(entry.avatar_id, entry.voice_id);

    setError(null);
    setOkMsg(null);
    setBusyId(entry.id);

    setLocalPersona(next);
    onPersonaChange(next);

    try {
      const saved = await persist(next, preset);
      const confirmed = { avatar_id: saved.avatar_id, voice_id: saved.voice_id };
      lastSavedRef.current = confirmed;
      setLocalPersona(confirmed);
      onPersonaChange(confirmed);
      setOkMsg(`${entry.shortName} ativo.`);
      if (isChat) setExpanded(false);
      await onSaved?.(confirmed);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Não foi possível trocar.";
      lastSavedRef.current = next;
      await persistLocal(next);
      await onSaved?.(next);
      setOkMsg(`${entry.shortName} ativo neste telemóvel.`);
      setError(
        msg
          ? `Servidor: ${msg} — tente sair e entrar de novo.`
          : "Servidor indisponível — escolha guardada no telemóvel."
      );
      if (isChat) setExpanded(false);
    } finally {
      setBusyId(null);
    }
  };

  if (isChat && !expanded) {
    return (
      <View style={[styles.wrap, styles.wrapChat]}>
        <Pressable
          onPress={() => !disabled && setExpanded(true)}
          disabled={disabled}
          style={({ pressed }) => [
            styles.chatCollapsed,
            {
              borderColor: colors.border,
              backgroundColor: colors.bgCard,
              opacity: disabled ? 0.5 : pressed ? 0.92 : 1,
            },
          ]}
          accessibilityRole="button"
          accessibilityLabel="Trocar assistente"
        >
          <Image
            source={avatarImageSource(activeCatalog.avatar_id)}
            style={styles.thumbCollapsed}
            resizeMode="cover"
          />
          <Text style={[styles.chatCollapsedName, { color: colors.text }]}>
            {activeCatalog.shortName}
          </Text>
          <Text style={[styles.chatCollapsedAction, { color: colors.primary }]}>Trocar</Text>
          <Text style={[styles.chatCollapsedChevron, { color: colors.textMuted }]}>▾</Text>
        </Pressable>
        {okMsg ? <Text style={[styles.ok, styles.okChat, { color: colors.success }]}>{okMsg}</Text> : null}
        {error ? <Text style={[styles.err, styles.errChat, { color: colors.danger }]}>{error}</Text> : null}
      </View>
    );
  }

  const renderCatalog = (opts: { compact?: boolean; onClose?: () => void }) => (
    <View style={[styles.wrap, opts.compact && styles.wrapChat]}>
      {opts.onClose ? (
        <Pressable onPress={opts.onClose} hitSlop={8} style={styles.hintChat}>
          <Text style={[styles.hintChatLink, { color: colors.primary }]}>
            Assistentes · fechar ✕
          </Text>
        </Pressable>
      ) : (
        <Text style={[styles.hint, { color: colors.textMuted }]}>
          12 assistentes · escolha o seu favorito
        </Text>
      )}
      <ScrollView
        style={opts.compact ? styles.catalogScroll : styles.catalogScrollSettings}
          nestedScrollEnabled
          showsVerticalScrollIndicator={false}
        >
          {CHAT_CATEGORIES.map((category) => {
            const items = avatarsByCategory(category);
            if (!items.length) return null;
            return (
              <View key={category} style={styles.catalogSection}>
                <Text style={[styles.catalogSectionTitle, { color: colors.textMuted }]}>
                  {AVATAR_CATEGORY_LABELS[category]}
                </Text>
                <View style={styles.catalogGrid}>
                  {items.map((entry) => {
                    const selected = localPersona.avatar_id === entry.avatar_id;
                    const loading = busyId === entry.id;
                    return (
                      <Pressable
                        key={entry.id}
                        style={[
                          styles.catalogCard,
                          {
                            borderColor: selected ? colors.primary : colors.border,
                            backgroundColor: selected ? colors.userBubble : colors.bgCard,
                            opacity: disabled && !selected ? 0.5 : 1,
                          },
                        ]}
                        onPress={() => void selectCatalogEntry(entry)}
                        disabled={!!busyId || disabled}
                      >
                        <Image
                          source={avatarImageSource(entry.avatar_id)}
                          style={styles.catalogThumb}
                          resizeMode="cover"
                        />
                        <Text
                          style={[styles.catalogName, { color: colors.text }]}
                          numberOfLines={1}
                        >
                          {entry.shortName}
                        </Text>
                        {loading ? (
                          <ActivityIndicator color={colors.primary} size="small" />
                        ) : selected ? (
                          <Text style={[styles.catalogActive, { color: colors.primary }]}>●</Text>
                        ) : null}
                      </Pressable>
                    );
                  })}
                </View>
              </View>
            );
          })}
        </ScrollView>
        {okMsg ? (
          <Text style={[styles.ok, opts.compact && styles.okChat, { color: colors.success }]}>{okMsg}</Text>
        ) : null}
        {error ? (
          <Text style={[styles.err, opts.compact && styles.errChat, { color: colors.danger }]}>{error}</Text>
        ) : null}
      </View>
  );

  if (isChat && expanded) {
    return renderCatalog({ compact: true, onClose: () => setExpanded(false) });
  }

  if (isSettings) {
    return renderCatalog({ compact: false });
  }

  return (
    <View style={[styles.wrap, isChat && styles.wrapChat]}>
      <View style={[styles.row, isChat && styles.rowChat]}>
        {PERSONA_PRESETS.map((p) => {
          const selected = active === p.id;
          const loading = busyId === p.id;
          return (
            <Pressable
              key={p.id}
              style={[
                isChat ? styles.cardChat : styles.card,
                {
                  borderColor: selected ? colors.primary : colors.border,
                  backgroundColor: selected ? colors.userBubble : colors.bgCard,
                  opacity: disabled && !selected ? 0.5 : 1,
                },
              ]}
              onPress={() => void selectPreset(p.id)}
              disabled={!!busyId || disabled}
            >
              <Image
                source={avatarImageSource(p.avatar_id)}
                style={isChat ? styles.thumbChat : styles.thumb}
                resizeMode="cover"
              />
              <Text style={[styles.cardTitle, isChat && styles.cardTitleChat, { color: colors.text }]}>
                {p.shortName}
              </Text>
              {isOnboarding ? (
                <Text style={[styles.cardSub, { color: colors.textMuted }]}>{p.description}</Text>
              ) : null}
              {loading ? (
                <ActivityIndicator color={colors.primary} style={{ marginTop: 6 }} />
              ) : (
                <Text style={[styles.badge, { color: colors.primaryLight }]}>
                  {isOnboarding ? "Continuar → check-in" : "Escolher"}
                </Text>
              )}
            </Pressable>
          );
        })}
      </View>
      {okMsg ? <Text style={[styles.ok, { color: colors.success }]}>{okMsg}</Text> : null}
      {error ? <Text style={[styles.err, { color: colors.danger }]}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: 8 },
  wrapChat: { marginBottom: 2, marginTop: 2 },
  chatCollapsed: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "center",
    gap: 10,
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 999,
    borderWidth: StyleSheet.hairlineWidth,
    maxWidth: "100%",
    flexShrink: 0,
  },
  thumbCollapsed: { width: 28, height: 28, borderRadius: 14, flexShrink: 0 },
  chatCollapsedName: { fontSize: 14, fontWeight: "700", flexShrink: 1, maxWidth: 120 },
  chatCollapsedAction: {
    fontSize: 13,
    fontWeight: "600",
    flexShrink: 0,
    paddingHorizontal: 2,
  },
  chatCollapsedChevron: { fontSize: 12, flexShrink: 0 },
  hint: { fontSize: 13, marginBottom: 10, lineHeight: 18 },
  hintChat: {
    fontSize: 12,
    marginBottom: 6,
    textAlign: "center",
    fontWeight: "600",
  },
  hintChatLink: { fontSize: 12, fontWeight: "600" },
  catalogScroll: { maxHeight: 220 },
  catalogScrollSettings: { maxHeight: 420 },
  catalogSection: { marginBottom: 10 },
  catalogSectionTitle: {
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: 6,
    textAlign: "center",
  },
  catalogGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "center",
    gap: 8,
  },
  catalogCard: {
    width: "30%",
    minWidth: 92,
    maxWidth: 110,
    borderRadius: 12,
    borderWidth: 2,
    paddingVertical: 6,
    paddingHorizontal: 4,
    alignItems: "center",
  },
  catalogThumb: { width: 44, height: 44, borderRadius: 22 },
  catalogName: { marginTop: 4, fontSize: 12, fontWeight: "700" },
  catalogMeta: { marginTop: 1, fontSize: 9, textAlign: "center" },
  catalogActive: { marginTop: 2, fontSize: 10, fontWeight: "700" },
  okChat: { marginTop: 4 },
  errChat: { marginTop: 4 },
  row: { flexDirection: "row", gap: 12 },
  rowChat: { gap: 10 },
  card: {
    flex: 1,
    borderRadius: 16,
    borderWidth: 2,
    padding: 10,
    alignItems: "center",
  },
  cardChat: {
    flex: 1,
    borderRadius: 14,
    borderWidth: 2,
    paddingVertical: 8,
    paddingHorizontal: 8,
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "center",
    gap: 8,
  },
  thumb: { width: 80, height: 80, borderRadius: 40 },
  thumbChat: { width: 40, height: 40, borderRadius: 20 },
  cardTitle: { marginTop: 8, fontSize: 15, fontWeight: "700" },
  cardTitleChat: { marginTop: 0, fontSize: 16, fontWeight: "800" },
  cardSub: { fontSize: 11, textAlign: "center", marginTop: 2 },
  badge: { marginTop: 6, fontSize: 12, fontWeight: "700" },
  ok: { marginTop: 8, fontSize: 12, textAlign: "center", fontWeight: "600" },
  err: { marginTop: 8, fontSize: 12, textAlign: "center" },
});
