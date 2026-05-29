import { router } from "expo-router";
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from "react-native";
import { checkoutUrlForTier } from "@/utils/planCheckout";
import { sendChatMessage } from "@/api/client";
import type { ChatMessage, SendChatResult } from "@/api/types";
import { ChatComposer } from "@/components/ChatComposer";
import { ChatPreview } from "@/components/ChatPreview";
import { AudioSpeedControl } from "@/components/AudioSpeedControl";
import { TokenUsageBar } from "@/components/TokenUsageBar";
import { ScreenShell } from "@/components/ScreenShell";
import { PersonaPicker } from "@/components/PersonaPicker";
import { SpeakingAvatar } from "@/components/SpeakingAvatar";
import { findAvatarInCatalog } from "@/constants/avatarCatalog";
import { accountPersona, isMaleAvatar } from "@/constants/personas";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/hooks/useDashboard";
import { useVoiceChat } from "@/hooks/useVoiceChat";
import { useColors } from "@/theme/ThemeContext";
import { chatSavedNotice, chatWarnings } from "@/utils/chatFeedback";
import { iosSafariMicHelpMessage } from "@/utils/webVoiceCapture";

export default function ChatScreen() {
  const colors = useColors();
  const { session } = useAuth();
  const { data, loading, refreshing, error, refresh, setPersona } = useDashboard();
  const [chatInput, setChatInput] = useState("");
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [chatNotice, setChatNotice] = useState<string | null>(null);
  const [pendingChat, setPendingChat] = useState<ChatMessage[]>([]);
  const [voiceReplies, setVoiceReplies] = useState(true);
  const [lastVoiceResult, setLastVoiceResult] = useState<SendChatResult | null>(null);

  const persona = accountPersona(data.me?.persona);
  const assistantName =
    findAvatarInCatalog(persona.avatar_id)?.shortName ??
    (isMaleAvatar(persona.avatar_id) ? "Leo" : "Luna");
  const voice = useVoiceChat();
  const micBusyRef = useRef(false);
  const micActive = voice.isRecording || voice.micSessionActive;
  const personaBusy = sending || micActive;
  const allowedSpeeds = useMemo(() => {
    const raw = data.access?.audio_speed_allowed;
    if (!raw?.length) return [1, 1.5];
    return raw.filter((s) => s !== 2);
  }, [data.access?.audio_speed_allowed]);

  useEffect(() => {
    if (voice.audioSpeed === 2) {
      voice.setAudioSpeed(1);
    }
  }, [voice.audioSpeed, voice.setAudioSpeed]);

  useEffect(() => {
    void voice.stopPlayback();
    setLastVoiceResult(null);
  }, [persona.avatar_id, persona.voice_id, voice.stopPlayback]);

  const profile = data.me?.profile as Record<string, unknown> | undefined;
  const profileName =
    (typeof profile?.full_name === "string" && profile.full_name.trim()) ||
    (typeof profile?.name === "string" && profile.name.trim()) ||
    (typeof profile?.first_name === "string" && profile.first_name.trim()) ||
    "";
  const emailAlias =
    typeof data.me?.email === "string" && data.me.email.includes("@")
      ? data.me.email.split("@")[0].trim().toLowerCase()
      : "";
  const nameLooksLikeEmailAlias =
    Boolean(profileName) &&
    Boolean(emailAlias) &&
    profileName.trim().toLowerCase() === emailAlias;
  const who = !nameLooksLikeEmailAlias && profileName ? profileName : "você";
  const checkout = data.me?.stripe_checkout;
  const userId = data.me?.user_id || session?.user?.id || "";
  const access = data.access;
  const userPlanTier = access?.plan_tier || "essential";
  const textLimit = access?.daily_text_messages_limit ?? access?.daily_messages_limit ?? 0;
  const textUsed = access?.daily_text_messages_used ?? access?.daily_messages_used ?? 0;
  const isDailyLimitFromAccess =
    access?.daily_text_messages_ok === false ||
    (textLimit > 0 && textUsed >= textLimit);
  const isDailyLimitFromError = /limite\s+di[aá]rio\s+atingido/i.test(chatError || "");
  const isDailyLimitReached = isDailyLimitFromAccess || isDailyLimitFromError;

  const withUserRef = (url: string | null) => {
    if (!url) return null;
    if (!userId) return url;
    const sep = url.includes("?") ? "&" : "?";
    if (url.includes("client_reference_id=")) return url;
    return `${url}${sep}client_reference_id=${encodeURIComponent(userId)}`;
  };

  const planOffers = [
    {
      id: "connection",
      label: "Conexão",
      cta: "Assinar Conexão",
      tag: "Entrada",
      highlight: false,
      url: withUserRef(checkoutUrlForTier("connection", checkout, "br")),
    },
    {
      id: "premium",
      label: "Premium",
      cta: "Assinar Premium",
      tag: "Mais escolhido",
      highlight: true,
      url: withUserRef(checkoutUrlForTier("premium", checkout, "br")),
    },
    {
      id: "total",
      label: "Total",
      cta: "Assinar Total",
      tag: "Sem limites",
      highlight: false,
      url: withUserRef(checkoutUrlForTier("total", checkout, "br")),
    },
  ].filter((p) => Boolean(p.url));

  const openCheckout = (url: string | null) => {
    if (url) {
      void Linking.openURL(url);
      return;
    }
    void router.push("/(main)/plans");
  };

  const chatMessages: ChatMessage[] = [...data.messages, ...pendingChat];

  const playVoice = async (result: SendChatResult) => {
    if (!voiceReplies) return;
    setLastVoiceResult(result);
    voice.unlockWebPlayback();
    const err = await voice.playReplyAudio(result, persona.voice_id, persona.avatar_id);
    if (err) {
      setChatNotice(
        "Toque em «Ouvir resposta» abaixo para ativar o som no iPhone."
      );
    }
  };

  const onListenLastReply = async () => {
    if (!lastVoiceResult) return;
    setChatError(null);
    voice.unlockWebPlayback();
    const err = await voice.playReplyAudio(
      lastVoiceResult,
      persona.voice_id,
      persona.avatar_id
    );
    if (err) setChatError(err);
  };

  const applyChatResult = (result: SendChatResult) => {
    setChatNotice(chatSavedNotice(result));
    setChatError(chatWarnings(result));
  };

  const onSendText = async () => {
    if (sending || !session) return;
    if (micActive) {
      await onMicPressOut();
      return;
    }
    const text = chatInput.trim();
    if (!text) return;
    voice.unlockWebPlayback();
    setChatError(null);
    setChatNotice(null);
    setChatInput("");
    setPendingChat([
      { role: "user", content: text },
      { role: "assistant", content: "…" },
    ]);
    setSending(true);
    try {
      const result = await sendChatMessage(text, voiceReplies);
      setPendingChat([
        { role: "user", content: text },
        { role: "assistant", content: result.reply },
      ]);
      applyChatResult(result);
      setPendingChat([]);
      void playVoice(result).catch((e) => {
        setChatError(e instanceof Error ? e.message : "Erro ao reproduzir áudio.");
      });
    } catch (e) {
      setPendingChat([{ role: "user", content: text }]);
      setChatError(e instanceof Error ? e.message : "Erro ao enviar.");
    } finally {
      void refresh();
      setSending(false);
    }
  };

  const onMicPressIn = async () => {
    if (sending || !session || micActive || micBusyRef.current) return;
    setChatError(null);
    setChatNotice(null);
    try {
      await voice.startRecording();
      if (voice.webMicMode === "recorder") {
        setChatNotice("A gravar… toque na seta ↑ para enviar.");
      }
    } catch (e) {
      setChatError(e instanceof Error ? e.message : "Microfone indisponível.");
    }
  };

  const onMicPressOut = async () => {
    if (!micActive || micBusyRef.current) return;
    if (!voice.isRecording) {
      setChatNotice("A preparar microfone… aguarde um instante.");
      return;
    }
    micBusyRef.current = true;
    voice.unlockWebPlayback();
    setChatNotice(null);
    setSending(true);
    setPendingChat([
      { role: "user", content: "Voz" },
      { role: "assistant", content: "…" },
    ]);
    try {
      const result = await voice.stopRecordingAndSend(voiceReplies);
      setPendingChat([
        { role: "user", content: "Voz" },
        { role: "assistant", content: result.reply },
      ]);
      applyChatResult(result);
      setPendingChat([]);
      void playVoice(result).catch((e) => {
        setChatError(e instanceof Error ? e.message : "Erro ao reproduzir áudio.");
      });
    } catch (e) {
      await voice.cancelRecording();
      setChatError(e instanceof Error ? e.message : "Erro na mensagem de voz.");
      setPendingChat([]);
    } finally {
      micBusyRef.current = false;
      void refresh();
      setSending(false);
    }
  };

  const onMicPress = async () => {
    if (sending || !session || micBusyRef.current) return;

    if (voice.webMicMode === "needs-https") {
      setChatNotice(null);
      setChatError(iosSafariMicHelpMessage());
      return;
    }

    if (micActive) {
      setChatNotice("A gravar… toque na seta ↑ para enviar.");
      return;
    }
    await onMicPressIn();
  };

  return (
    <ScreenShell immersive>
      <View style={styles.body}>
        <View style={[styles.avatarSection, { backgroundColor: colors.bg, borderBottomColor: colors.border }]}>
          <SpeakingAvatar
            avatarId={persona.avatar_id}
            subtitle={`Olá, ${who}. Como posso te ajudar hoje?`}
            isSpeaking={voice.isSpeaking}
            isListening={micActive}
            compact
            hideLabel
          />
          <PersonaPicker
            colors={colors}
            variant="chat"
            planTier={userPlanTier}
            persona={persona}
            disabled={personaBusy}
            onPersonaChange={(p) => setPersona(p.avatar_id, p.voice_id)}
            onSaved={refresh}
          />
          <View style={styles.voiceRow}>
            <Text style={[styles.voiceLabel, { color: colors.textMuted }]}>Áudio</Text>
            <Switch
              value={voiceReplies}
              onValueChange={setVoiceReplies}
              trackColor={{ true: colors.primaryLight, false: colors.border }}
              thumbColor={voiceReplies ? colors.primary : "#e4e4e7"}
            />
            {voiceReplies && lastVoiceResult?.reply ? (
              <Pressable
                onPress={() => void onListenLastReply()}
                style={({ pressed }) => [
                  styles.listenBtnInline,
                  {
                    borderColor: colors.primary,
                    backgroundColor: colors.bgCard,
                    opacity: pressed ? 0.9 : 1,
                  },
                ]}
                accessibilityRole="button"
                accessibilityLabel="Ouvir resposta do assistente"
              >
                <Text style={[styles.listenBtnInlineText, { color: colors.primary }]}>
                  Ouvir resposta
                </Text>
              </Pressable>
            ) : null}
            <View style={styles.speedDivider} />
            <AudioSpeedControl
              colors={colors}
              value={voice.audioSpeed}
              onChange={voice.setAudioSpeed}
              disabled={!voiceReplies}
              allowedSpeeds={allowedSpeeds}
            />
          </View>
          <TokenUsageBar colors={colors} access={data.access} />
        </View>

        <ScrollView
          style={styles.messagesScroll}
          contentContainerStyle={styles.messagesContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={refresh}
              tintColor={colors.primary}
            />
          }
          keyboardShouldPersistTaps="handled"
        >
          {loading && !refreshing ? (
            <ActivityIndicator color={colors.primary} style={{ marginVertical: 16 }} />
          ) : null}

          {error ? (
            <Text style={[styles.error, { color: colors.danger }]}>{error}</Text>
          ) : null}

          {!loading && chatMessages.length > 0 ? (
            <ChatPreview messages={chatMessages} assistantLabel={assistantName} />
          ) : !loading ? (
            <Text style={[styles.empty, { color: colors.textMuted }]}>
              Escreve ou usa o microfone para começar.
            </Text>
          ) : null}

          {isDailyLimitReached ? (
            <View style={[styles.limitBox, { borderColor: colors.border, backgroundColor: colors.bgCard }]}>
              <Text style={[styles.limitTitle, { color: colors.text }]}>
                Limite diário atingido
              </Text>
              <Text style={[styles.limitSub, { color: colors.textMuted }]}>
                Assine um plano mensal para continuar ou espere até 00:00 para usar de novo.
              </Text>
              <View style={styles.limitActions}>
                {planOffers.map((offer) => (
                  <Pressable
                    key={offer.id}
                    onPress={() => openCheckout(offer.url)}
                    style={({ pressed }) => [
                      styles.planCard,
                      {
                        backgroundColor: offer.highlight ? colors.primary : colors.bg,
                        borderColor: offer.highlight ? colors.primary : colors.border,
                        opacity: pressed ? 0.9 : 1,
                      },
                    ]}
                  >
                    <Text
                      style={[
                        styles.planTag,
                        {
                          color: offer.highlight ? "#fff" : colors.primary,
                          backgroundColor: offer.highlight
                            ? "rgba(255,255,255,0.22)"
                            : colors.primaryLight,
                        },
                      ]}
                    >
                      {offer.tag}
                    </Text>
                    <Text
                      style={[
                        styles.planName,
                        { color: offer.highlight ? "#fff" : colors.text },
                      ]}
                    >
                      {offer.label}
                    </Text>
                    <Text
                      style={[
                        styles.limitBtnText,
                        { color: offer.highlight ? "#fff" : colors.primary },
                      ]}
                    >
                      {offer.cta}
                    </Text>
                  </Pressable>
                ))}
              </View>
              <Pressable onPress={() => void router.push("/(main)/plans")}>
                <Text style={[styles.allPlansLink, { color: colors.primary }]}>
                  Ver todos os planos
                </Text>
              </Pressable>
            </View>
          ) : null}
        </ScrollView>

        <View style={styles.composerWrap}>
          <ChatComposer
          value={chatInput}
          onChangeText={setChatInput}
          onSend={onSendText}
          sending={sending}
          isRecording={micActive}
          voiceReady={voice.isRecording}
          onMicPress={onMicPress}
          error={isDailyLimitReached ? null : chatError}
          notice={chatNotice}
          />
        </View>
      </View>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  body: { flex: 1, overflow: "hidden" },
  composerWrap: {
    flexShrink: 0,
    zIndex: 2,
  },
  listenBtnInline: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 999,
    borderWidth: 1,
    flexShrink: 0,
  },
  listenBtnInlineText: { fontSize: 12, fontWeight: "700" },
  avatarSection: {
    flexShrink: 0,
    paddingTop: 44,
    paddingHorizontal: 16,
    paddingBottom: 6,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  messagesScroll: { flex: 1, minHeight: 0 },
  messagesContent: {
    flexGrow: 1,
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 12,
  },
  voiceRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    flexWrap: "wrap",
    gap: 8,
    marginBottom: 4,
  },
  speedDivider: {
    width: StyleSheet.hairlineWidth,
    height: 22,
    backgroundColor: "#d4d4d8",
  },
  voiceLabel: { fontSize: 13, fontWeight: "500" },
  empty: { textAlign: "center", fontSize: 14, marginTop: 8 },
  error: { fontSize: 13, textAlign: "center", marginBottom: 8 },
  limitBox: {
    marginTop: 12,
    marginBottom: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 12,
    padding: 12,
  },
  limitTitle: { fontSize: 15, fontWeight: "800", marginBottom: 6, textAlign: "center" },
  limitSub: { fontSize: 13, lineHeight: 18, marginBottom: 10, textAlign: "center" },
  allPlansLink: { fontSize: 13, fontWeight: "700", textAlign: "center", marginTop: 8 },
  limitActions: { flexDirection: "row", gap: 8, flexWrap: "wrap", justifyContent: "center" },
  planCard: {
    minWidth: 102,
    borderRadius: 12,
    borderWidth: 1,
    paddingVertical: 8,
    paddingHorizontal: 10,
    alignItems: "center",
  },
  planTag: {
    fontSize: 10,
    fontWeight: "700",
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 3,
    overflow: "hidden",
    marginBottom: 6,
  },
  planName: { fontSize: 13, fontWeight: "800", marginBottom: 4 },
  limitBtnText: { fontSize: 12, fontWeight: "700" },
});
