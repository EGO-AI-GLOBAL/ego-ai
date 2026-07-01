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
import { allowsInAppPlanPurchase, IOS_CHAT_BLOCKED_PLACEHOLDER, IOS_DAILY_LIMIT_ALERT, IOS_TRIAL_END_ALERT } from "@/utils/iosAppStoreBilling";
import { sendChatMessage, submitNightDumpBlob, submitNightDumpFromUri, submitNightDumpText, completeWellnessJourneyStep } from "@/api/client";
import type { ChatMessage, SendChatResult } from "@/api/types";
import { AppGradientBackground } from "@/components/AppGradientBackground";
import { ChatComposer } from "@/components/ChatComposer";
import { ChatPreview } from "@/components/ChatPreview";
import { AvatarEngagementCard } from "@/components/AvatarEngagementCard";
import { getComposerPlaceholder } from "@/constants/chatQuickActions";
import {
  ChatScheduleBanner,
  extractScheduleBannerItems,
} from "@/components/ChatScheduleBanner";
import { ChatDayStrip } from "@/components/ChatDayStrip";
import { EgoDeBolsoChatCard } from "@/components/EgoDeBolsoChatCard";
import { MoodGardenWidgetCard } from "@/components/moodMonsters/MoodGardenWidgetCard";
import { ScreenShell } from "@/components/ScreenShell";
import { PersonaPicker } from "@/components/PersonaPicker";
import { TrialExpiredBanner } from "@/components/TrialExpiredBanner";
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
import { useKeyboardHeight } from "@/hooks/useKeyboardHeight";
import { useVoiceChat } from "@/hooks/useVoiceChat";
import { useColors } from "@/theme/ThemeContext";
import { chatSavedNotice, chatWarnings } from "@/utils/chatFeedback";
import { enrichChatError } from "@/utils/chatError";
import { ChatWidgetErrorBoundary } from "@/monitoring/ChatWidgetErrorBoundary";
import { ChatRouteErrorBoundary } from "@/monitoring/ChatRouteErrorBoundary";
import {
  estimateTokenDelta,
  patchAccessWithTokenDelta,
} from "@/utils/usageStats";
import {
  chatResultChangedData,
  mergeChatIntoDashboard,
} from "@/utils/mergeChatDashboard";
import {
  presentSharedCalendarEventNow,
  syncSharedCalendarLocalNotifications,
} from "@/utils/sharedCalendarNotifications";
import { ritualChatPrompt } from "@/constants/dailyRituals";
import type { DailyRitualId } from "@/constants/dailyRituals";
import {
  buildSaveCelebrationLine,
  buildSaveCelebrationSpeech,
  chatResultHasScheduleSave,
} from "@/constants/saveCelebration";
import { consumePendingAvatarCongrats } from "@/storage/pendingAvatarCongrats";
import { consumeMonsterChatNotice } from "@/utils/monsterChatNotice";
import { consumePendingRitual } from "@/storage/pendingRitual";
import { computeDayProgress } from "@/utils/dayProgress";
import { streakAvatarSubtitle } from "@/utils/streakReactions";
import { recordAvatarChat } from "@/utils/avatarEngagement";
import { chatStreakSubtitle, getChatStreak, recordChatStreakDay } from "@/utils/chatStreak";
import { isTrialExpired } from "@/utils/trialAccess";
import {
  buildChatOnboardingMessage,
  buildChatOnboardingSpeech,
} from "@/constants/chatOnboarding";
import {
  isChatOnboardingDone,
  markChatOnboardingDone,
} from "@/storage/chatOnboarding";
import { appendLocalAssistantMessage } from "@/storage/chatHistoryLocal";
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
  return (
    <ChatRouteErrorBoundary>
      <ChatScreenInner />
    </ChatRouteErrorBoundary>
  );
}

function ChatScreenInner() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const { session } = useAuth();
  const { data, loading, refreshing, error, refresh, refreshAccess, setPersona, mergeChatResult, mergeWellnessJourney } =
    useDashboard();
  const userId = data.me?.user_id?.trim() ?? session?.user?.id?.trim() ?? "";

  const onPersonaSaved = useCallback(
    async (choice: { avatar_id: string; voice_id: string }) => {
      await setPersona(choice.avatar_id, choice.voice_id);
      if (userId) {
        await markPersonaConfiguredLocal(userId);
        await saveLocalPersonaChoice(userId, choice);
      }
    },
    [setPersona, userId]
  );

  const onEngagementAvatarOpen = useCallback(
    (avatarId: string) => {
      const entry = findAvatarInCatalog(avatarId);
      if (!entry) return;
      void onPersonaSaved({ avatar_id: entry.avatar_id, voice_id: entry.voice_id });
    },
    [onPersonaSaved]
  );
  const [chatInput, setChatInput] = useState("");
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [chatNotice, setChatNotice] = useState<string | null>(null);
  const [pendingChat, setPendingChat] = useState<ChatMessage[]>([]);
  const [autoPlayVoice, setAutoPlayVoice] = useState(false);
  const [lastChatResult, setLastChatResult] = useState<SendChatResult | null>(null);
  const [scheduleBannerDismissed, setScheduleBannerDismissed] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfCharCount, setPdfCharCount] = useState(0);
  const [pdfPartCount, setPdfPartCount] = useState(0);
  /** Evita perder anexos se o utilizador adicionar outro PDF antes do refresh do perfil. */
  const pdfAccumRef = useRef("");
  const pdfCountRef = useRef(0);
  const ritualHandledRef = useRef(false);
  const ritualPendingRef = useRef<DailyRitualId | null>(null);
  const [nightDumpMode, setNightDumpMode] = useState(false);
  const [saveCelebrationLine, setSaveCelebrationLine] = useState<string | null>(null);
  const [chatStreakDays, setChatStreakDays] = useState(0);
  const [dashboardSettled, setDashboardSettled] = useState(false);
  const [widgetsReady, setWidgetsReady] = useState(false);
  const [bolsoCelebrate, setBolsoCelebrate] = useState(false);
  const bolsoMissionsRef = useRef(data.wellness_journey?.missions_today ?? 0);
  const bolsoCelebrateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    bolsoMissionsRef.current = data.wellness_journey?.missions_today ?? 0;
  }, [data.wellness_journey?.missions_today]);

  useEffect(() => {
    return () => {
      if (bolsoCelebrateTimerRef.current) clearTimeout(bolsoCelebrateTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!loading) setDashboardSettled(true);
  }, [loading]);

  useEffect(() => {
    const id = requestAnimationFrame(() => setWidgetsReady(true));
    return () => cancelAnimationFrame(id);
  }, []);

  useEffect(() => {
    void loadAutoPlayVoice().then(setAutoPlayVoice);
  }, []);

  useEffect(() => {
    if (!userId) return;
    void getChatStreak(userId).then(setChatStreakDays);
  }, [userId]);

  const cancelNightDump = useCallback(() => {
    setNightDumpMode(false);
    setChatNotice(null);
  }, []);

  const dayProgress = useMemo(() => computeDayProgress(data), [data]);
  const composerPlaceholder = useMemo(
    () => getComposerPlaceholder(dayProgress.period),
    [dayProgress.period]
  );

  const scheduleBannerItems = useMemo(() => {
    if (!lastChatResult || scheduleBannerDismissed) return [];
    return extractScheduleBannerItems(lastChatResult, data);
  }, [lastChatResult, scheduleBannerDismissed, data]);

  const persona = accountPersona(data.me?.persona);
  const assistantName =
    findAvatarInCatalog(persona.avatar_id)?.shortName ??
    (isMaleAvatar(persona.avatar_id) ? "Leo" : "Luna");
  const voice = useVoiceChat();

  const trackJourneyStep = useCallback(
    (step: "chat" | "voice") => {
      const before = bolsoMissionsRef.current;
      void completeWellnessJourneyStep(step).then((j) => {
        if (!j) return;
        const after = j.missions_today ?? 0;
        if (after > before) {
          setBolsoCelebrate(true);
          if (bolsoCelebrateTimerRef.current) clearTimeout(bolsoCelebrateTimerRef.current);
          bolsoCelebrateTimerRef.current = setTimeout(() => setBolsoCelebrate(false), 1400);
        }
        mergeWellnessJourney(j);
      });
    },
    [mergeWellnessJourney]
  );

  const onBolsoTalkMission = useCallback((draft: string) => {
    setChatInput(draft);
    setChatNotice("Missão no campo abaixo — envie ou edite antes de mandar.");
    setChatError(null);
  }, []);

  const finishNightDump = useCallback(
    (dump: { items?: { length: number }; comfort_reply?: string }) => {
      const n = dump.items?.length ?? 0;
      setChatNotice(
        n > 0
          ? `Desabafo recebido. Amanhã de manhã abra a Agenda — a ${assistantName} separou ${n} item(ns) para você confirmar.`
          : "Desabafo guardado. Amanhã de manhã veja a Agenda — ou puxe para baixo para atualizar."
      );
      void refresh({ skipNotifications: true });
    },
    [refresh, assistantName]
  );

  const startNightDump = useCallback(() => {
    void voice.stopPlayback();
    void voice.cancelRecording();
    setNightDumpMode(true);
    setChatError(null);
    setChatNotice(
      "Desabafo das 22h: fale ou escreva. Amanhã de manhã a agenda aparece para você confirmar."
    );
  }, [voice.stopPlayback, voice.cancelRecording]);

  const {
    messages: localMessages,
    setMessages: setLocalMessages,
    ready: localChatReady,
    historyForApi,
    saveExchange,
  } = useLocalChatHistory(userId, data.messages);
  const onboardingSeedRef = useRef(false);
  const micBusyRef = useRef(false);
  const messagesScrollRef = useRef<ScrollView>(null);
  /** Se true, mantém o scroll no fim ao crescer o histórico (entrada no chat / nova msg). */
  const stickToBottomRef = useRef(true);
  const keyboard = useKeyboardHeight();
  const keyboardHeight = keyboard.height;
  const keyboardBottomInset = keyboard.bottomInset;
  const keyboardOpen = keyboardHeight > 0;
  const micActive = voice.isRecording || voice.micSessionActive || voice.isPhoneCall;
  const personaBusy =
    sending || micActive || voice.isSpeaking || voice.isPreparingAudio;
  const showAvatarSection =
    !keyboardOpen ||
    sending ||
    micActive ||
    voice.isPreparingAudio ||
    voice.isSpeaking;
  const audioStatusLabel = voice.isPhoneCall
    ? voice.isSpeaking
      ? "Em chamada — a falar…"
      : voice.isAssistantThinking
        ? "Em chamada — a pensar…"
        : voice.isUserSpeaking
          ? "Em chamada — a ouvir…"
          : "Em chamada — fale quando quiser"
    : sending
      ? "A pensar…"
      : voice.isPreparingAudio
        ? "A preparar áudio…"
        : voice.isSpeaking
          ? "A falar…"
          : null;

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
  const displayWho = !nameLooksLikeEmailAlias && profileName ? profileName.trim() : undefined;
  const avatarSubtitle = voice.isPhoneCall
    ? voice.isAssistantThinking
      ? `${assistantName} está pensando…`
      : voice.isUserSpeaking
        ? `${assistantName} está ouvindo…`
        : `Conversa com ${assistantName} — fale quando quiser.`
    : voice.isSpeaking
      ? `${assistantName} está falando…`
      : micActive
        ? `${assistantName} está ouvindo…`
        : chatStreakSubtitle(chatStreakDays, assistantName) ??
          streakAvatarSubtitle(data.streak, assistantName) ??
          `${assistantName} · pronto para ajudar`;
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
  const trialExpired = isTrialExpired(access);
  const showChatWidgets = dashboardSettled && widgetsReady && (!loading || refreshing);

  const onNightDumpPress = useCallback(() => {
    if (trialExpired) {
      Alert.alert(
        "Teste encerrado",
        allowsInAppPlanPurchase()
          ? "Assine um plano para continuar o desabafo e o chat."
          : IOS_TRIAL_END_ALERT
      );
      return;
    }
    if (isDailyLimitReached) {
      Alert.alert(
        "Limite diário",
        allowsInAppPlanPurchase()
          ? "O desabafo usa a mesma cota do chat. Espere até 00:00 ou assine um plano para continuar."
          : IOS_DAILY_LIMIT_ALERT
      );
      return;
    }
    if (nightDumpMode) cancelNightDump();
    else startNightDump();
  }, [trialExpired, isDailyLimitReached, nightDumpMode, cancelNightDump, startNightDump]);

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
    if (!allowsInAppPlanPurchase()) return;
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

  useEffect(() => {
    if (!localChatReady || !userId || loading || onboardingSeedRef.current) return;
    if ((data.messages?.length ?? 0) > 0) {
      void markChatOnboardingDone(userId);
      return;
    }
    if (localMessages.length > 0) return;

    onboardingSeedRef.current = true;
    void (async () => {
      const pendingRitual = await consumePendingRitual();
      if (pendingRitual) {
        ritualPendingRef.current = pendingRitual;
        await markChatOnboardingDone(userId);
        return;
      }
      if (await isChatOnboardingDone(userId)) return;
      const displayName =
        !nameLooksLikeEmailAlias && profileName ? profileName.trim() : undefined;
      const male = isMaleAvatar(persona.avatar_id);
      const text = buildChatOnboardingMessage(assistantName, displayName, male, persona.avatar_id);
      const speech = buildChatOnboardingSpeech(assistantName, displayName, male, persona.avatar_id);
      const next = await appendLocalAssistantMessage(userId, text, { onboarding: true });
      setLocalMessages(next);
      setLastChatResult({ reply: speech });
      await markChatOnboardingDone(userId);
      stickToBottomRef.current = true;
      scrollMessagesToEnd(true);
      setChatNotice("Leia a mensagem de boas-vindas acima. Ligue «Ouvir ao responder» para ouvir.");
    })();
  }, [
    localChatReady,
    userId,
    loading,
    localMessages.length,
    data.messages?.length,
    assistantName,
    profileName,
    nameLooksLikeEmailAlias,
    persona.voice_id,
    persona.avatar_id,
    scrollMessagesToEnd,
    setLocalMessages,
  ]);

  useFocusEffect(
    useCallback(() => {
      stickToBottomRef.current = true;
      if (localChatReady && chatMessages.length > 0) {
        scrollMessagesToEnd(false);
      }
      if (userId) {
        void consumeMonsterChatNotice().then((monster) => {
          if (monster) {
            setChatNotice(monster);
            return;
          }
          void consumePendingAvatarCongrats(userId).then((line) => {
            if (line) setChatNotice(line);
          });
        });
      }
    }, [localChatReady, chatMessages.length, scrollMessagesToEnd, userId])
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

  /** Voz do avatar: toggle «Ouvir ao responder». */
  const playVoice = async (result: SendChatResult) => {
    setLastChatResult(result);
    voice.unlockWebPlayback();
    if (!autoPlayVoice) {
      return;
    }
    await voice.stopPlayback();
    setChatNotice(null);
    setChatError(null);
    const err = await voice.playReplyAudio(
      result,
      persona.voice_id,
      persona.avatar_id
    );
    if (err) {
      setChatError(err);
    }
  };

  const onAutoPlayVoiceChange = (enabled: boolean) => {
    setAutoPlayVoice(enabled);
    void saveAutoPlayVoice(enabled);
    if (!enabled) {
      void voice.stopPlayback();
      setChatNotice(null);
    }
  };

  const applyChatResult = useCallback(
    (result: SendChatResult, userLabel?: string) => {
      if (result.access) {
        mergeChatResult(result);
      } else if (result.reply && !chatWarnings(result) && data.access) {
        const delta = estimateTokenDelta(userLabel || "", result.reply);
        const patched = patchAccessWithTokenDelta(data.access, delta);
        if (patched) {
          mergeChatResult({ reply: result.reply, access: patched });
        }
      }
      setChatNotice(chatSavedNotice(result, data));
      const warn = chatWarnings(result);
      setChatError(warn ? enrichChatError(warn, result.access ?? data.access) : null);
      setScheduleBannerDismissed(false);
      void refreshAccess();
    },
    [data, mergeChatResult, refreshAccess]
  );

  const afterChatSaved = useCallback(
    async (result: SendChatResult, _userText?: string) => {
      if (chatResultHasScheduleSave(result)) {
        const line = buildSaveCelebrationLine(assistantName, result);
        setSaveCelebrationLine(line);
        if (line) {
          setChatNotice(line);
        }
        const speech = buildSaveCelebrationSpeech(assistantName, result);
        if (speech && autoPlayVoice) {
          voice.unlockWebPlayback();
          void voice.replayLastText(speech, persona.voice_id, persona.avatar_id);
        }
      }
      if (chatResultChangedData(result) || result.access) {
        mergeChatResult(result);
        const merged = mergeChatIntoDashboard(data, result);
        void syncSharedCalendarLocalNotifications(merged.shared_calendars ?? []);
        for (const ev of result.shared_events_saved ?? []) {
          const cal =
            data.shared_calendars?.find((c) => String(c.id) === String(ev.calendar_id))
              ?.name ||
            ev.calendar_name ||
            data.shared_calendars?.[0]?.name ||
            "Agenda";
          void presentSharedCalendarEventNow({
            calendarName: cal,
            title: String(ev.title || "Compromisso"),
            scheduledAt: String(ev.scheduled_at || ""),
          });
        }
      }
    },
    [data, mergeChatResult, assistantName, persona.avatar_id, persona.voice_id, voice, autoPlayVoice]
  );

  const pdfSummaryPrompt =
    pdfPartCount > 1
      ? "Resuma o conjunto de documentos anexados (várias partes), de forma clara e objetiva em português. " +
        "Integre todas as partes num único resumo coerente. Use tópicos curtos: assunto principal, pontos importantes e conclusão. " +
        "Se for contrato ou relatório, destaque datas, valores e obrigações relevantes."
      : "Resuma este documento anexado de forma clara e objetiva em português. " +
        "Use tópicos curtos: assunto principal, pontos importantes e conclusão. " +
        "Se for contrato ou relatório, destaque datas, valores e obrigações relevantes.";

  const onMicPressIn = async () => {
    if (sending || micBusyRef.current) return;
    if (!session) {
      setChatError("Sessão expirada. Faça login de novo para usar o microfone.");
      return;
    }
    if (micActive) return;
    setChatError(null);
    setChatNotice(null);
    try {
      await voice.startRecording(historyForApi());
      if (voice.activeVoiceMode === "realtime") {
        setChatNotice("A ouvir… toque ↑ para enviar.");
      } else if (voice.webUsesSpeechToText) {
        setChatNotice("A ouvir… toque ↑ para enviar.");
      } else if (voice.webMicMode === "recorder") {
        setChatNotice("A gravar… toque na seta ↑ para enviar.");
      }
    } catch (e) {
      setChatError(e instanceof Error ? e.message : "Microfone indisponível.");
    }
  };

  const onMicPressOut = async () => {
    if (!micActive || micBusyRef.current) return;
    micBusyRef.current = true;
    if (!voice.isRecording) {
      const ready = await voice.waitForRecording(800);
      if (!ready) {
        micBusyRef.current = false;
        await voice.cancelRecording();
        setChatNotice(null);
        setChatError("Microfone não iniciou. Toque no microfone, fale 2s e toque na seta ↑.");
        return;
      }
    }
    voice.unlockWebPlayback();
    setChatError(null);
    setChatNotice("A ouvir o áudio…");
    setSending(true);
    setPendingChat([
      { role: "user", content: "Voz" },
      { role: "assistant", content: "…" },
    ]);
    let voiceToPlay: SendChatResult | null = null;
    try {
      if (nightDumpMode) {
        setChatNotice("A processar desabafo…");
        const raw = await voice.stopRecordingRaw();
        const dump = raw.blob
          ? await submitNightDumpBlob(raw.blob)
          : await submitNightDumpFromUri({ uri: raw.uri || "", audioMime: raw.mime });
        const userLabel = dump.transcript?.trim() || "Desabafo da noite";
        const reply =
          dump.comfort_reply?.trim() ||
          `Recebi o que você compartilhou. Amanhã de manhã confirme na Agenda.`;
        setPendingChat([
          { role: "user", content: userLabel },
          { role: "assistant", content: reply },
        ]);
        await saveExchange(userLabel, reply, { userWasVoice: true });
        setPendingChat([]);
        setNightDumpMode(false);
        finishNightDump(dump);
        setLastChatResult({ reply });
        if (autoPlayVoice) {
          void voice.replayLastText(reply, persona.voice_id, persona.avatar_id);
        } else {
          setChatNotice("Resposta pronta. Ligue «Ouvir ao responder» para ouvir.");
        }
        return;
      }
      const result = await voice.stopRecordingAndSend(false, historyForApi(), {
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
      applyChatResult(result, userLabel);
      await afterChatSaved(result, userLabel);
      if (userId) {
        void recordAvatarChat(userId, persona.avatar_id);
        void recordChatStreakDay(userId).then(setChatStreakDays);
      }
      trackJourneyStep("voice");
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
      if (result.voice_engine === "openai_realtime") {
        setChatNotice("Resposta em voz reproduzida.");
      } else if (result.reply?.trim() && autoPlayVoice) {
        voiceToPlay = result;
      } else if (result.reply?.trim()) {
        setChatNotice("Resposta pronta. Ligue «Ouvir ao responder» para ouvir.");
      }
    } catch (e) {
      await voice.cancelRecording();
      setChatError(
        enrichChatError(
          e instanceof Error ? e.message : "Erro na mensagem de voz.",
          data.access
        )
      );
      setPendingChat([]);
    } finally {
      micBusyRef.current = false;
      void refreshAccess();
      setSending(false);
    }
    if (voiceToPlay) {
      void playVoice(voiceToPlay).catch((e) => {
        setChatError(e instanceof Error ? e.message : "Erro ao reproduzir áudio.");
      });
    }
  };

  const onMicPress = async () => {
    if (sending || micBusyRef.current) return;
    if (!session) {
      setChatError("Sessão expirada. Faça login de novo para usar o microfone.");
      return;
    }
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
      setChatNotice("A gravar… toque na seta ↑ para enviar.");
      return;
    }

    await onMicPressIn();
  };

  const sendMessageText = useCallback(
    async (text: string, userLabel: string, opts?: { forceVoice?: boolean }) => {
      if (sending || !session || !text.trim()) return;
      if (trialExpired) {
        Alert.alert(
          "Teste encerrado",
          allowsInAppPlanPurchase()
            ? "Assine um plano para continuar conversando com seu assistente."
            : IOS_TRIAL_END_ALERT
        );
        return;
      }
      if (micActive) {
        await onMicPressOut();
        return;
      }
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
        const result = await sendChatMessage(text, false, historyForApi());
        setPendingChat([
          { role: "user", content: userLabel },
          { role: "assistant", content: result.reply },
        ]);
        applyChatResult(result, userLabel);
        await afterChatSaved(result, userLabel);
        if (userId) {
          void recordAvatarChat(userId, persona.avatar_id);
          void recordChatStreakDay(userId).then(setChatStreakDays);
        }
        trackJourneyStep("chat");
        await saveExchange(userLabel, result.reply);
        setPendingChat([]);
        setLastChatResult(result);
        const wantVoice = autoPlayVoice || Boolean(opts?.forceVoice);
        if (wantVoice) {
          void playVoice(result).catch((e) => {
            setChatError(e instanceof Error ? e.message : "Erro ao reproduzir áudio.");
          });
        } else {
          setChatNotice(null);
        }
      } catch (e) {
        setPendingChat([{ role: "user", content: userLabel }]);
        setChatError(
          enrichChatError(e instanceof Error ? e.message : "Erro ao enviar.", data.access)
        );
      } finally {
        void refreshAccess();
        setSending(false);
      }
    },
    [
      sending,
      session,
      micActive,
      onMicPressOut,
      autoPlayVoice,
      applyChatResult,
      afterChatSaved,
      saveExchange,
      historyForApi,
      refreshAccess,
      playVoice,
      scrollMessagesToEnd,
      voice,
      userId,
      persona.avatar_id,
      persona.voice_id,
      trackJourneyStep,
      trialExpired,
    ]
  );

  useEffect(() => {
    if (!localChatReady || loading || sending || ritualHandledRef.current) return;
    void (async () => {
      if (!ritualPendingRef.current) {
        const stored = await consumePendingRitual();
        if (stored) ritualPendingRef.current = stored;
      }
      const ritual = ritualPendingRef.current;
      if (!ritual) return;
      ritualHandledRef.current = true;
      ritualPendingRef.current = null;
      if (ritual === "evening") {
        startNightDump();
        const intro =
          "Desabafo agora: use o microfone ou escreva. Depois confirme na Agenda (Agendar / Excluir).";
        setChatNotice(intro);
        return;
      }
      if (ritual === "reveal") {
        router.push("/(main)/agenda");
        return;
      }
      const labels: Record<DailyRitualId, string> = {
        reveal: "Amanhã revelado",
        morning: "Briefing",
        afternoon: "Ponto",
        evening: "Desabafo",
      };
      const prompt = ritualChatPrompt(ritual, assistantName, persona.avatar_id);
      if (ritual === "morning" && !autoPlayVoice) {
        setAutoPlayVoice(true);
        void saveAutoPlayVoice(true);
      }
      await sendMessageText(prompt, labels[ritual], { forceVoice: ritual === "morning" });
    })();
  }, [
    localChatReady,
    loading,
    sending,
    assistantName,
    sendMessageText,
    autoPlayVoice,
    startNightDump,
  ]);

  const onSendText = async () => {
    if (micBusyRef.current) return;
    if (voice.isRecording || voice.micSessionActive) {
      await onMicPressOut();
      return;
    }
    const typed = chatInput.trim();
    if (nightDumpMode && typed) {
      if (!session) {
        setChatError("Sessão expirada. Faça login de novo para enviar o desabafo.");
        return;
      }
      if (trialExpired) {
        Alert.alert(
          "Teste encerrado",
          allowsInAppPlanPurchase()
            ? "Assine um plano para continuar o desabafo e o chat."
            : IOS_TRIAL_END_ALERT
        );
        return;
      }
      if (isDailyLimitReached) {
        Alert.alert(
          "Limite diário",
          allowsInAppPlanPurchase()
            ? "O desabafo usa a mesma cota do chat. Espere até 00:00 ou assine um plano para continuar."
            : IOS_DAILY_LIMIT_ALERT
        );
        return;
      }
      setSending(true);
      setChatError(null);
      setChatNotice("A processar desabafo…");
      stickToBottomRef.current = true;
      setPendingChat([
        { role: "user", content: typed },
        { role: "assistant", content: "…" },
      ]);
      scrollMessagesToEnd(true);
      try {
        const dump = await submitNightDumpText(typed);
        const reply =
          dump.comfort_reply?.trim() ||
          "Recebi. Amanhã de manhã confirme na Agenda.";
        setPendingChat([
          { role: "user", content: typed },
          { role: "assistant", content: reply },
        ]);
        await saveExchange(typed, reply, { userWasVoice: false });
        setChatInput("");
        setNightDumpMode(false);
        setPendingChat([]);
        finishNightDump(dump);
        if (autoPlayVoice) {
          await voice.replayLastText(reply, persona.voice_id, persona.avatar_id);
        }
      } catch (e) {
        setPendingChat([]);
        setChatNotice(null);
        setChatError(
          enrichChatError(
            e instanceof Error ? e.message : "Erro no desabafo.",
            data.access
          )
        );
      } finally {
        void refreshAccess();
        setSending(false);
      }
      return;
    }
    const text = typed || (pdfCharCount > 0 ? pdfSummaryPrompt : "");
    if (!text) return;
    await sendMessageText(text, typed || "Resumo do documento");
  };

  useEffect(() => {
    if (!keyboardOpen) return;
    stickToBottomRef.current = true;
    scrollMessagesToEnd(true);
  }, [keyboardOpen, scrollMessagesToEnd]);

  const keyboardOffset = Platform.OS === "ios" ? insets.top + 56 : 0;

  const chatBody = (
    <>
        {showAvatarSection ? (
        <View
          style={[
            styles.avatarSection,
            {
              paddingTop: 10,
              backgroundColor: "transparent",
              borderBottomColor: colors.glassBorder,
            },
          ]}
        >
          <ChatWidgetErrorBoundary name="speaking-avatar">
            <SpeakingAvatar
              avatarId={persona.avatar_id}
              subtitle={avatarSubtitle}
              isSpeaking={voice.isSpeaking}
              isListening={
                voice.isPhoneCall
                  ? voice.isUserSpeaking && !voice.isSpeaking && !voice.isAssistantThinking
                  : (voice.isRecording || micActive) &&
                    !voice.isSpeaking &&
                    !voice.isPreparingAudio &&
                    !sending
              }
              isThinking={
                (voice.isPhoneCall && voice.isAssistantThinking) ||
                voice.isPreparingAudio ||
                (sending && !voice.isSpeaking && !voice.isPreparingAudio)
              }
              compact
              hideLabel
            />
          </ChatWidgetErrorBoundary>
          <ChatWidgetErrorBoundary name="persona-picker">
            <PersonaPicker
              colors={colors}
              variant="chat"
              planTier={userPlanTier}
              persona={persona}
              disabled={personaBusy}
              onPersonaChange={(p) => void setPersona(p.avatar_id, p.voice_id)}
              onSaved={onPersonaSaved}
            />
          </ChatWidgetErrorBoundary>
          <View style={styles.voiceControls}>
            <View style={styles.voiceToggleRow}>
              <Text style={[styles.voiceLabel, { color: colors.textMuted }]}>
                Ouvir ao responder
              </Text>
              <Switch
                value={autoPlayVoice}
                onValueChange={onAutoPlayVoiceChange}
                trackColor={{ true: colors.primaryLight, false: colors.border }}
                thumbColor={autoPlayVoice ? colors.primary : "#e4e4e7"}
              />
            </View>
          </View>
          {audioStatusLabel ? (
            <Text style={[styles.audioStatus, { color: colors.primary }]}>
              {audioStatusLabel}
            </Text>
          ) : null}
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

          {error && !localChatReady ? (
            <Text style={[styles.error, { color: colors.danger }]}>{error}</Text>
          ) : null}

          {!loading || refreshing ? (
            <TrialExpiredBanner
              colors={colors}
              access={data.access}
              streak={data.streak}
              journey={data.wellness_journey}
              care={data.daily_care}
              planOffers={planOffers}
              onOpenCheckout={openCheckout}
            />
          ) : null}

          {!loading || refreshing ? (
            <ChatDayStrip
              colors={colors}
              progress={dayProgress}
              access={data.access}
              assistantName={assistantName}
              displayName={displayWho}
              onPressNext={() => {
                const item = dayProgress.nextItem;
                if (item) {
                  void sendMessageText(`Alterar ou cancelar: ${item.title}`, item.title);
                }
              }}
            />
          ) : null}

          {showChatWidgets && userId ? (
            <ChatWidgetErrorBoundary name="avatar-engagement">
              <AvatarEngagementCard
                userId={userId}
                currentAvatarId={persona.avatar_id}
                colors={colors}
                onOpenAvatar={onEngagementAvatarOpen}
              />
            </ChatWidgetErrorBoundary>
          ) : null}

          {showChatWidgets ? (
            <ChatWidgetErrorBoundary name="mood-garden">
              <MoodGardenWidgetCard colors={colors} care={data.daily_care} />
            </ChatWidgetErrorBoundary>
          ) : null}

          {showChatWidgets ? (
            <ChatWidgetErrorBoundary name="ego-bolso">
              <EgoDeBolsoChatCard
                colors={colors}
                journey={data.wellness_journey}
                onCareHint={setChatNotice}
                onTalkMission={onBolsoTalkMission}
                celebrate={bolsoCelebrate}
              />
            </ChatWidgetErrorBoundary>
          ) : null}

          {localChatReady && chatMessages.length > 0 ? (
            <ChatPreview messages={chatMessages} assistantLabel={assistantName} />
          ) : localChatReady && !loading && !isDailyLimitReached ? (
            <Text style={[styles.empty, { color: colors.textMuted }]}>
              Escreva ou fale com {assistantName}.
            </Text>
          ) : null}

          {scheduleBannerItems.length > 0 ? (
            <ChatScheduleBanner
              colors={colors}
              items={scheduleBannerItems}
              assistantName={assistantName}
              celebrationLine={saveCelebrationLine}
              onDismiss={() => {
                setScheduleBannerDismissed(true);
                setSaveCelebrationLine(null);
              }}
            />
          ) : null}

          {isDailyLimitReached ? (
            <View style={[styles.limitBox, { borderColor: colors.border, backgroundColor: colors.bgCard }]}>
              <Text style={[styles.limitTitle, { color: colors.text }]}>
                Limite diário atingido
              </Text>
              <Text style={[styles.limitSub, { color: colors.textMuted }]}>
                {allowsInAppPlanPurchase()
                  ? "Assine um plano mensal para continuar ou espere até 00:00 para usar de novo."
                  : "Espere até 00:00 para usar de novo ou entre com uma conta que já tenha plano ativo."}
              </Text>
              {allowsInAppPlanPurchase() ? (
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
              ) : null}
            </View>
          ) : null}
        </ScrollView>

        <View style={styles.composerWrap}>
          <View style={[styles.dumpStrip, { borderTopColor: colors.border, backgroundColor: colors.bg }]}>
            <View style={styles.voiceActionsRow}>
              <Pressable
                onPress={onNightDumpPress}
                disabled={sending || (micActive && !nightDumpMode)}
                style={({ pressed }) => [
                  styles.actionChip,
                  {
                    borderColor: colors.primary,
                    backgroundColor: nightDumpMode ? colors.primary : colors.bgCard,
                    opacity:
                      sending || (micActive && !nightDumpMode)
                        ? 0.5
                        : pressed
                          ? 0.88
                          : 1,
                  },
                ]}
                accessibilityRole="button"
                accessibilityLabel={
                  nightDumpMode ? "Cancelar desabafo" : "Desabafo agora"
                }
              >
                <Text
                  style={[
                    styles.actionChipText,
                    { color: nightDumpMode ? "#fff" : colors.primary },
                  ]}
                >
                  Desabafo agora
                </Text>
              </Pressable>
            </View>
            {nightDumpMode ? (
              <View
                style={[
                  styles.nightDumpBanner,
                  { backgroundColor: colors.primaryTint, borderColor: colors.primary },
                ]}
              >
                <Text style={[styles.nightDumpTitle, { color: colors.text }]}>
                  Modo desabafo ativo
                </Text>
                <Text style={[styles.nightDumpBody, { color: colors.textMuted }]}>
                  Fale ou escreva tudo. Amanhã de manhã {assistantName} separa sua agenda — você só
                  confirma com Agendar ou Excluir.
                </Text>
                <Pressable onPress={cancelNightDump} hitSlop={8}>
                  <Text style={{ color: colors.primary, fontWeight: "700", fontSize: 13 }}>
                    Cancelar desabafo
                  </Text>
                </Pressable>
              </View>
            ) : null}
          </View>
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
            placeholder={
              trialExpired
                ? allowsInAppPlanPurchase()
                  ? "Assine um plano para continuar…"
                  : IOS_CHAT_BLOCKED_PLACEHOLDER
                : nightDumpMode
                ? "Escreva o desabafo e toque enviar…"
                : composerPlaceholder
            }
            sending={sending || trialExpired}
            isRecording={voice.isRecording}
            micSessionActive={voice.micSessionActive}
            voiceReady={voice.isRecording && !trialExpired}
            onMicPress={onMicPress}
            onPdfPress={() => onDocPress()}
            pdfLoading={pdfLoading}
            pdfActive={pdfCharCount > 0}
            pdfPartCount={pdfPartCount}
            error={chatError}
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
      <AppGradientBackground variant="chat" style={styles.body}>
      <KeyboardAvoidingView
        style={[
          styles.bodyInner,
          keyboardBottomInset > 0 && { paddingBottom: keyboardBottomInset },
        ]}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        enabled={Platform.OS === "ios"}
        keyboardVerticalOffset={keyboardOffset}
      >
        {chatBody}
      </KeyboardAvoidingView>
      </AppGradientBackground>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  body: { flex: 1 },
  bodyInner: { flex: 1 },
  composerWrap: {
    flexShrink: 0,
    zIndex: 2,
    width: "100%",
    maxWidth: "100%",
  },
  dumpStrip: {
    paddingHorizontal: 12,
    paddingTop: 8,
    paddingBottom: 4,
    borderTopWidth: StyleSheet.hairlineWidth,
    gap: 8,
  },
  actionChip: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 999,
    borderWidth: 1,
    minWidth: 128,
    alignItems: "center",
  },
  actionChipText: { fontSize: 13, fontWeight: "800" },
  avatarSection: {
    flexShrink: 0,
    width: "100%",
    maxWidth: "100%",
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
  voiceActionsRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    flexWrap: "wrap",
    gap: 8,
    maxWidth: "100%",
  },
  voiceControls: {
    width: "100%",
    alignItems: "center",
    gap: 8,
    marginBottom: 4,
  },
  voiceToggleRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
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
  nightDumpBanner: {
    width: "100%",
    marginTop: 4,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 12,
    borderWidth: 1,
    gap: 6,
  },
  nightDumpTitle: { fontSize: 13, fontWeight: "800", textAlign: "center" },
  nightDumpBody: { fontSize: 12, lineHeight: 17, textAlign: "center" },
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
