import * as DocumentPicker from "expo-document-picker";
import * as ImagePicker from "expo-image-picker";
import { router, useFocusEffect } from "expo-router";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
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
import {
  markPersonaConfiguredLocal,
  saveLocalPersonaChoice,
} from "@/storage/personaPrefs";
import { useLocalChatHistory } from "@/hooks/useLocalChatHistory";
import type { AudioPlaybackSpeed } from "@/constants/audioSpeed";
import { useKeyboardHeight } from "@/hooks/useKeyboardHeight";
import { useVoiceChat } from "@/hooks/useVoiceChat";
import { useColors } from "@/theme/ThemeContext";
import { chatSavedNotice, chatWarnings } from "@/utils/chatFeedback";
import { loadAutoPlayVoice, saveAutoPlayVoice } from "@/storage/chatPrefs";
import { iosSafariMicHelpMessage } from "@/utils/webVoiceCapture";
import {
  clearPdfContext,
  DOCUMENT_PICKER_MIME_TYPES,
  extractPdfUploads,
  isSupportedDocName,
  mergePdfContextParts,
  pdfAttachmentCountFromProfile,
  pdfContextFromProfile,
  persistPdfContext,
} from "@/utils/pdfContext";

function isImageAttachmentName(name: string): boolean {
  return /\.(jpe?g|png|webp|hei[cf])$/i.test(name || "");
}

export default function ChatScreen() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const { session } = useAuth();
  const { data, loading, refreshing, error, refresh, setPersona } = useDashboard();
  const userId = data.me?.user_id?.trim() ?? session?.user?.id?.trim() ?? "";

  const onPersonaSaved = useCallback(
    async (choice: { avatar_id: string; voice_id: string }) => {
      setPersona(choice.avatar_id, choice.voice_id);
      if (userId) {
        await markPersonaConfiguredLocal(userId);
        await saveLocalPersonaChoice(userId, choice);
      }
    },
    [setPersona, userId]
  );
  const [chatInput, setChatInput] = useState("");
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [chatNotice, setChatNotice] = useState<string | null>(null);
  const [pendingChat, setPendingChat] = useState<ChatMessage[]>([]);
  const [autoPlayVoice, setAutoPlayVoice] = useState(false);
  const [lastChatResult, setLastChatResult] = useState<SendChatResult | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfCharCount, setPdfCharCount] = useState(0);
  const [pdfPartCount, setPdfPartCount] = useState(0);
  /** Evita perder anexos se o utilizador adicionar outro PDF antes do refresh do perfil. */
  const pdfAccumRef = useRef("");
  const pdfCountRef = useRef(0);

  useEffect(() => {
    void loadAutoPlayVoice().then(setAutoPlayVoice);
  }, []);

  const persona = accountPersona(data.me?.persona);
  const assistantName =
    findAvatarInCatalog(persona.avatar_id)?.shortName ??
    (isMaleAvatar(persona.avatar_id) ? "Leo" : "Luna");
  const voice = useVoiceChat();
  const {
    messages: localMessages,
    ready: localChatReady,
    historyForApi,
    saveExchange,
  } = useLocalChatHistory(userId, data.messages);
  const micBusyRef = useRef(false);
  const messagesScrollRef = useRef<ScrollView>(null);
  /** Se true, mantém o scroll no fim ao crescer o histórico (entrada no chat / nova msg). */
  const stickToBottomRef = useRef(true);
  const keyboard = useKeyboardHeight();
  const keyboardHeight = keyboard.height;
  const keyboardBottomInset = keyboard.bottomInset;
  const keyboardOpen = keyboardHeight > 0;
  const micActive = voice.isRecording || voice.micSessionActive || voice.isPhoneCall;
  const personaBusy = sending || micActive;
  /** Planos pagos: só 1,5x e 2x no UI; Essencial: sem botões (velocidade normal). */
  const allowedSpeeds = useMemo((): AudioPlaybackSpeed[] => {
    const raw = data.access?.audio_speed_allowed;
    if (!raw?.length) return [];
    const out: AudioPlaybackSpeed[] = [];
    if (raw.includes(1.5)) out.push(1.5);
    if (raw.includes(2)) out.push(2);
    return out;
  }, [data.access?.audio_speed_allowed]);

  const showSpeedControl = autoPlayVoice && allowedSpeeds.length > 0;
  const audioStatusLabel = voice.isPhoneCall
    ? voice.isSpeaking
      ? "Em chamada — a falar…"
      : voice.isAssistantThinking
        ? "Em chamada — a pensar…"
        : voice.isUserSpeaking
          ? "Em chamada — a ouvir…"
          : "Em chamada — fale quando quiser"
    : voice.isPreparingAudio
      ? "A preparar áudio…"
      : voice.isSpeaking
        ? "A falar…"
        : null;

  useEffect(() => {
    if (allowedSpeeds.length === 0 && voice.audioSpeed !== 1) {
      voice.setAudioSpeed(1);
    }
  }, [allowedSpeeds.length, voice.audioSpeed, voice.setAudioSpeed]);

  useEffect(() => {
    void voice.stopPlayback();
    setLastChatResult(null);
  }, [persona.avatar_id, persona.voice_id, voice.stopPlayback]);

  const profile = data.me?.profile as Record<string, unknown> | undefined;

  useEffect(() => {
    const text = pdfContextFromProfile(profile);
    const count = pdfAttachmentCountFromProfile(profile);
    pdfAccumRef.current = text;
    pdfCountRef.current = count;
    setPdfCharCount(text.length);
    setPdfPartCount(count);
  }, [profile]);

  const ingestAttachmentFiles = async (
    files: Array<{ uri: string; name: string }>
  ) => {
    if (!files.length) return;
    setPdfLoading(true);
    setChatError(null);
    const readingImage = files.some((f) => isImageAttachmentName(f.name));
    setChatNotice(readingImage ? "A ler texto da foto…" : "A ler documento…");
    const extracted = await extractPdfUploads(files);
    const prevCount = pdfCountRef.current;
    const merged = mergePdfContextParts(pdfAccumRef.current, extracted.text);
    const newCount = prevCount + files.length;
    const { charCount, text: stored } = await persistPdfContext(merged, profile, {
      attachmentCount: newCount,
    });
    pdfAccumRef.current = stored;
    pdfCountRef.current = newCount;
    setPdfCharCount(charCount);
    setPdfPartCount(newCount);
    const warn =
      extracted.warnings.length > 0 ? ` (${extracted.warnings[0]})` : "";
    const partLabel =
      newCount === 1
        ? "1 parte anexada"
        : `${newCount.toLocaleString("pt-BR")} partes anexadas`;
    setChatNotice(
      `${partLabel} (${charCount.toLocaleString("pt-BR")} caracteres). ` +
        `Doc para mais partes; depois toque em «Enviar resumo» acima da caixa de mensagem.${warn}`
    );
    void refresh();
  };

  const onPickDocument = async () => {
    if (!session || pdfLoading || sending || micActive) return;
    try {
      const picked = await DocumentPicker.getDocumentAsync({
        type: [...DOCUMENT_PICKER_MIME_TYPES],
        multiple: false,
        copyToCacheDirectory: true,
      });
      if (picked.canceled) return;
      const assets = picked.assets ?? [];
      if (!assets.length) return;
      const files = assets.map((a) => ({
        uri: a.uri,
        name: a.name || "documento.txt",
      }));
      await ingestAttachmentFiles(files);
    } catch (e) {
      setChatError(
        e instanceof Error ? e.message : "Não foi possível carregar o documento."
      );
      setChatNotice(null);
    } finally {
      setPdfLoading(false);
    }
  };

  const onPickImage = async (source: "gallery" | "camera") => {
    if (!session || pdfLoading || sending || micActive) return;
    try {
      const perm =
        source === "camera"
          ? await ImagePicker.requestCameraPermissionsAsync()
          : await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) {
        setChatError(
          "Permissão negada. Ative câmara ou fotos nas definições do telemóvel."
        );
        return;
      }
      const result =
        source === "camera"
          ? await ImagePicker.launchCameraAsync({
              mediaTypes: ["images"],
              quality: 0.85,
            })
          : await ImagePicker.launchImageLibraryAsync({
              mediaTypes: ["images"],
              quality: 0.85,
              allowsMultipleSelection: false,
            });
      if (result.canceled || !result.assets?.length) return;
      const asset = result.assets[0];
      const mime = (asset.mimeType || "").toLowerCase();
      const ext = mime.includes("png")
        ? "png"
        : mime.includes("webp")
          ? "webp"
          : "jpg";
      let name = asset.fileName || `foto-${Date.now()}.${ext}`;
      if (!isSupportedDocName(name)) {
        name = `foto-${Date.now()}.${ext}`;
      }
      await ingestAttachmentFiles([{ uri: asset.uri, name }]);
    } catch (e) {
      setChatError(
        e instanceof Error ? e.message : "Não foi possível ler a foto."
      );
      setChatNotice(null);
    } finally {
      setPdfLoading(false);
    }
  };

  const onDocPress = () => {
    if (!session || pdfLoading || sending || micActive) return;
    if (Platform.OS === "web") {
      void onPickDocument();
      return;
    }
    Alert.alert(
      "Anexar ao chat",
      "Adicione uma parte de cada vez (ficheiro ou foto). Quando terminar, use «Enviar resumo» no banner.",
      [
        { text: "Ficheiro (PDF, Word…)", onPress: () => void onPickDocument() },
        { text: "Galeria (foto)", onPress: () => void onPickImage("gallery") },
        { text: "Tirar foto", onPress: () => void onPickImage("camera") },
        { text: "Cancelar", style: "cancel" },
      ]
    );
  };

  const onClearPdf = async () => {
    if (!session || pdfLoading) return;
    setPdfLoading(true);
    setChatError(null);
    try {
      await clearPdfContext(profile);
      pdfAccumRef.current = "";
      pdfCountRef.current = 0;
      setPdfCharCount(0);
      setPdfPartCount(0);
      setChatNotice("Documentos removidos.");
      void refresh();
    } catch (e) {
      setChatError(e instanceof Error ? e.message : "Não foi possível limpar o PDF.");
    } finally {
      setPdfLoading(false);
    }
  };
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
  const avatarSubtitle = voice.isPhoneCall
    ? voice.liveCallSubtitle?.trim() ||
      (voice.isAssistantThinking
        ? "Só um instante…"
        : voice.isUserSpeaking
          ? "Estou a ouvir-te."
          : "Conversa naturalmente — estou na linha.")
    : `Olá, ${who}. Como posso te ajudar hoje?`;
  const checkout = data.me?.stripe_checkout;
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

  const chatMessages: ChatMessage[] = [...localMessages, ...pendingChat];

  const lastMessageScrollKey = useMemo(() => {
    if (!chatMessages.length) return "0";
    const last = chatMessages[chatMessages.length - 1];
    return `${chatMessages.length}:${last?.role ?? ""}:${(last?.content ?? "").length}`;
  }, [chatMessages]);

  const scrollMessagesToEnd = useCallback((animated = true) => {
    const attempt = () => {
      messagesScrollRef.current?.scrollToEnd({ animated });
    };
    requestAnimationFrame(attempt);
    setTimeout(attempt, 16);
    setTimeout(attempt, 120);
    setTimeout(attempt, 320);
  }, []);

  useFocusEffect(
    useCallback(() => {
      stickToBottomRef.current = true;
      if (localChatReady && chatMessages.length > 0) {
        scrollMessagesToEnd(false);
      }
    }, [localChatReady, chatMessages.length, scrollMessagesToEnd])
  );

  useEffect(() => {
    if (!localChatReady || chatMessages.length === 0) return;
    stickToBottomRef.current = true;
    scrollMessagesToEnd(false);
  }, [localChatReady, chatMessages.length, scrollMessagesToEnd]);

  useEffect(() => {
    if (!localChatReady || chatMessages.length === 0 || !stickToBottomRef.current) {
      return;
    }
    scrollMessagesToEnd(true);
  }, [lastMessageScrollKey, localChatReady, chatMessages.length, scrollMessagesToEnd]);

  const onMessagesScroll = useCallback(
    (e: { nativeEvent: { layoutMeasurement: { height: number }; contentOffset: { y: number }; contentSize: { height: number } } }) => {
      const { layoutMeasurement, contentOffset, contentSize } = e.nativeEvent;
      const nearBottom =
        layoutMeasurement.height + contentOffset.y >= contentSize.height - 80;
      stickToBottomRef.current = nearBottom;
    },
    []
  );

  const onMessagesContentSizeChange = useCallback(() => {
    if (stickToBottomRef.current) {
      scrollMessagesToEnd(false);
    }
  }, [scrollMessagesToEnd]);

  const playVoice = async (
    result: SendChatResult,
    opts?: { manual?: boolean }
  ) => {
    setLastChatResult(result);
    voice.unlockWebPlayback();
    if (!opts?.manual && !autoPlayVoice) {
      return;
    }
    await voice.stopPlayback();
    setChatNotice("A preparar áudio…");
    setChatError(null);
    const err = await voice.playReplyAudio(
      result,
      persona.voice_id,
      persona.avatar_id
    );
    if (err) {
      setChatNotice(null);
      setChatError(err);
      return;
    }
    setChatNotice(null);
  };

  const onListenLastReply = async () => {
    if (!lastChatResult?.reply?.trim()) return;
    await voice.stopPlayback();
    await playVoice(lastChatResult, { manual: true });
  };

  const onAutoPlayVoiceChange = (enabled: boolean) => {
    setAutoPlayVoice(enabled);
    void saveAutoPlayVoice(enabled);
    if (!enabled) {
      void voice.stopPlayback();
      setChatNotice(null);
    }
  };

  const applyChatResult = (result: SendChatResult) => {
    setChatNotice(chatSavedNotice(result));
    setChatError(chatWarnings(result));
  };

  const pdfSummaryPrompt =
    pdfPartCount > 1
      ? "Resuma o conjunto de documentos anexados (várias partes), de forma clara e objetiva em português. " +
        "Integre todas as partes num único resumo coerente. Use tópicos curtos: assunto principal, pontos importantes e conclusão. " +
        "Se for contrato ou relatório, destaque datas, valores e obrigações relevantes."
      : "Resuma este documento anexado de forma clara e objetiva em português. " +
        "Use tópicos curtos: assunto principal, pontos importantes e conclusão. " +
        "Se for contrato ou relatório, destaque datas, valores e obrigações relevantes.";

  const onSendText = async () => {
    if (sending || !session) return;
    if (micActive) {
      await onMicPressOut();
      return;
    }
    const typed = chatInput.trim();
    const text =
      typed ||
      (pdfCharCount > 0 ? pdfSummaryPrompt : "");
    if (!text) return;
    const userLabel = typed || "Resumo do documento";
    voice.unlockWebPlayback();
    setChatError(null);
    setChatNotice(null);
    setChatInput("");
    stickToBottomRef.current = true;
    setPendingChat([
      { role: "user", content: userLabel },
      { role: "assistant", content: "…" },
    ]);
    scrollMessagesToEnd(true);
    setSending(true);
    try {
      const result = await sendChatMessage(text, autoPlayVoice, historyForApi());
      setPendingChat([
        { role: "user", content: userLabel },
        { role: "assistant", content: result.reply },
      ]);
      applyChatResult(result);
      await saveExchange(userLabel, result.reply);
      setPendingChat([]);
      setLastChatResult(result);
      if (autoPlayVoice) {
        void playVoice(result).catch((e) => {
          setChatError(e instanceof Error ? e.message : "Erro ao reproduzir áudio.");
        });
      } else {
        setChatNotice("Resposta pronta. Toque em «Ouvir resposta» para ouvir.");
      }
    } catch (e) {
      setPendingChat([{ role: "user", content: userLabel }]);
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
      await voice.startRecording(historyForApi());
      if (voice.activeVoiceMode === "realtime") {
        setChatNotice("Fale… voz em tempo real (OpenAI). Toque Enviar voz quando terminar.");
      } else if (voice.webUsesSpeechToText) {
        setChatNotice("Fale… o Chrome converte em texto (rápido). Toque Enviar voz quando terminar.");
      } else if (voice.webMicMode === "recorder") {
        setChatNotice("A gravar… toque no microfone outra vez para enviar.");
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
    setChatError(null);
    setChatNotice("A ouvir o áudio…");
    setSending(true);
    setPendingChat([
      { role: "user", content: "Voz" },
      { role: "assistant", content: "…" },
    ]);
    try {
      const result = await voice.stopRecordingAndSend(autoPlayVoice, historyForApi(), {
        onDelta: (_chunk, full) => {
          setChatNotice("A responder…");
          setPendingChat([
            { role: "user", content: "Voz" },
            { role: "assistant", content: full || "…" },
          ]);
        },
      });
      const userLabel = result.user_transcript?.trim() || "Voz";
      setPendingChat([
        { role: "user", content: userLabel },
        { role: "assistant", content: result.reply },
      ]);
      applyChatResult(result);
      if (result.voice_engine === "openai_realtime") {
        setChatNotice("A responder…");
      }
      await saveExchange(
        result.user_transcript?.trim() || "",
        result.reply,
        { userWasVoice: !result.user_transcript?.trim() }
      );
      setPendingChat([]);
      setLastChatResult(result);
      if (autoPlayVoice && result.voice_engine !== "openai_realtime") {
        void playVoice(result).catch((e) => {
          setChatError(e instanceof Error ? e.message : "Erro ao reproduzir áudio.");
        });
      } else if (result.voice_engine === "openai_realtime") {
        setChatNotice("Resposta em voz reproduzida.");
      } else {
        setChatNotice("Resposta pronta. Toque em «Ouvir resposta» para ouvir.");
      }
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
    if (voice.isPhoneCall) {
      setChatNotice("Use «Encerrar chamada» para sair do modo telefone.");
      return;
    }

    if (voice.webMicMode === "needs-https") {
      setChatNotice(null);
      setChatError(iosSafariMicHelpMessage());
      return;
    }

    if (micActive) {
      if (voice.isRecording) {
        await onMicPressOut();
      } else {
        setChatNotice("A preparar microfone… aguarde um instante.");
      }
      return;
    }
    await onMicPressIn();
  };

  useEffect(() => {
    if (!keyboardOpen) return;
    stickToBottomRef.current = true;
    scrollMessagesToEnd(true);
  }, [keyboardOpen, scrollMessagesToEnd]);

  const keyboardOffset = Platform.OS === "ios" ? insets.top + 56 : 0;

  const chatBody = (
    <>
        {!keyboardOpen ? (
        <View
          style={[
            styles.avatarSection,
            { paddingTop: 10, backgroundColor: colors.bg, borderBottomColor: colors.border },
          ]}
        >
          <SpeakingAvatar
            avatarId={persona.avatar_id}
            subtitle={avatarSubtitle}
            isSpeaking={voice.isSpeaking}
            isListening={
              voice.isPhoneCall
                ? voice.isUserSpeaking && !voice.isSpeaking && !voice.isAssistantThinking
                : micActive && !voice.isSpeaking
            }
            isThinking={voice.isPhoneCall && voice.isAssistantThinking}
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
            onSaved={onPersonaSaved}
          />
          <View style={styles.voiceRow}>
            <Text style={[styles.voiceLabel, { color: colors.textMuted }]}>
              Ouvir ao responder
            </Text>
            <Switch
              value={autoPlayVoice}
              onValueChange={onAutoPlayVoiceChange}
              trackColor={{ true: colors.primaryLight, false: colors.border }}
              thumbColor={autoPlayVoice ? colors.primary : "#e4e4e7"}
            />
            {lastChatResult?.reply ? (
              <Pressable
                onPress={() => void onListenLastReply()}
                disabled={voice.isPreparingAudio || sending}
                style={({ pressed }) => [
                  styles.listenBtnInline,
                  {
                    borderColor: colors.primary,
                    backgroundColor: colors.bgCard,
                    opacity:
                      voice.isPreparingAudio || sending
                        ? 0.5
                        : pressed
                          ? 0.9
                          : 1,
                  },
                ]}
                accessibilityRole="button"
                accessibilityLabel="Ouvir resposta do assistente"
              >
                <Text style={[styles.listenBtnInlineText, { color: colors.primary }]}>
                  {voice.isPreparingAudio ? "A preparar…" : "Ouvir resposta"}
                </Text>
              </Pressable>
            ) : null}
            {showSpeedControl ? (
              <>
                <View style={styles.speedDivider} />
                <AudioSpeedControl
                  colors={colors}
                  value={voice.audioSpeed}
                  onChange={voice.setAudioSpeed}
                  disabled={!autoPlayVoice || voice.isPreparingAudio}
                  allowedSpeeds={allowedSpeeds}
                />
              </>
            ) : null}
          </View>
          {audioStatusLabel ? (
            <Text style={[styles.audioStatus, { color: colors.primary }]}>
              {audioStatusLabel}
            </Text>
          ) : null}
          <TokenUsageBar colors={colors} access={data.access} />
        </View>
        ) : null}

        <ScrollView
          ref={messagesScrollRef}
          style={styles.messagesScroll}
          contentContainerStyle={styles.messagesContent}
          onContentSizeChange={onMessagesContentSizeChange}
          onScroll={onMessagesScroll}
          scrollEventThrottle={16}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={refresh}
              tintColor={colors.primary}
            />
          }
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode="on-drag"
        >
          {loading && !refreshing && !localChatReady ? (
            <ActivityIndicator color={colors.primary} style={{ marginVertical: 16 }} />
          ) : null}

          {error ? (
            <Text style={[styles.error, { color: colors.danger }]}>{error}</Text>
          ) : null}

          {localChatReady && chatMessages.length > 0 ? (
            <ChatPreview messages={chatMessages} assistantLabel={assistantName} />
          ) : localChatReady && !loading ? (
            <Text style={[styles.empty, { color: colors.textMuted }]}>
              Escreve, anexa documento ou foto (Doc) ou usa o microfone.
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
          {pdfCharCount > 0 ? (
            <View
              style={[
                styles.pdfBannerCard,
                { backgroundColor: colors.bgCard, borderColor: colors.primary },
              ]}
            >
              <Text style={[styles.pdfBannerText, { color: colors.textMuted }]}>
                {pdfPartCount > 1
                  ? `${pdfPartCount.toLocaleString("pt-BR")} partes no documento`
                  : "Documento anexado"}
                {" · "}
                {pdfCharCount.toLocaleString("pt-BR")} caracteres
              </Text>
              <View style={styles.pdfBannerActions}>
                <Pressable
                  onPress={() => void onSendText()}
                  disabled={sending || pdfLoading || micActive}
                  style={({ pressed }) => [
                    styles.pdfSendBtn,
                    {
                      backgroundColor: colors.primary,
                      opacity: sending || pdfLoading || micActive || pressed ? 0.75 : 1,
                    },
                  ]}
                  accessibilityRole="button"
                  accessibilityLabel="Enviar resumo do documento"
                >
                  <Text style={styles.pdfSendBtnText}>Enviar resumo</Text>
                </Pressable>
                <Pressable
                  onPress={() => void onClearPdf()}
                  disabled={pdfLoading}
                  accessibilityRole="button"
                  accessibilityLabel="Remover documentos do contexto"
                >
                  <Text style={[styles.pdfClearLink, { color: colors.primary }]}>Limpar</Text>
                </Pressable>
              </View>
            </View>
          ) : null}
          <ChatComposer
            value={chatInput}
            onChangeText={setChatInput}
            onSend={onSendText}
            sending={sending}
            isRecording={micActive}
            voiceReady={voice.isRecording && !voice.isPhoneCall}
            onMicPress={onMicPress}
            onPdfPress={() => onDocPress()}
            pdfLoading={pdfLoading}
            pdfActive={pdfCharCount > 0}
            pdfPartCount={pdfPartCount}
            error={isDailyLimitReached ? null : chatError}
            notice={chatNotice}
            onInputFocus={() => {
              stickToBottomRef.current = true;
              scrollMessagesToEnd(true);
            }}
          />
        </View>
    </>
  );

  return (
    <ScreenShell immersive>
      <KeyboardAvoidingView
        style={[
          styles.body,
          keyboardBottomInset > 0 && { paddingBottom: keyboardBottomInset },
        ]}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        enabled={Platform.OS === "ios"}
        keyboardVerticalOffset={keyboardOffset}
      >
        {chatBody}
      </KeyboardAvoidingView>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  body: { flex: 1 },
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
    paddingHorizontal: 16,
    paddingBottom: 4,
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
  audioStatus: {
    fontSize: 12,
    fontWeight: "600",
    textAlign: "center",
    marginBottom: 4,
  },
  empty: { textAlign: "center", fontSize: 14, marginTop: 8 },
  pdfBannerCard: {
    marginHorizontal: 16,
    marginBottom: 6,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 12,
    borderWidth: 1,
    gap: 8,
  },
  pdfBannerText: { fontSize: 12, fontWeight: "500", textAlign: "center" },
  pdfBannerActions: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 14,
    flexWrap: "wrap",
  },
  pdfSendBtn: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 999,
  },
  pdfSendBtnText: { color: "#fff", fontSize: 13, fontWeight: "800" },
  pdfClearLink: { fontSize: 12, fontWeight: "700" },
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
