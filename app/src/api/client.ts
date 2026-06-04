import axios, { AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from "axios";
import * as FileSystem from "expo-file-system";
import { API_V1 } from "@/constants/config";
import { resolveSpeechVoiceId } from "@/constants/personas";
import { getPlayIntegrityToken } from "@/security/playIntegrity";
import { getWebOrigin } from "@/utils/webLocation";
import { reportApiFailure } from "@/monitoring/errorReporter";
import type {
  AccessInfo,
  ApiErr,
  AuthSession,
  DashboardData,
  HealthInfo,
  MeData,
  PlanCatalogItem,
  ChatHistoryPayload,
  Reminder,
  SendChatResult,
  SharedCalendar,
  SharedCalendarEvent,
  SharedCalendarMember,
} from "./types";

const STORAGE_KEY = "ego_auth_session";

const apiBase = API_V1.endsWith("/") ? API_V1 : `${API_V1}/`;

let memorySession: AuthSession | null = null;
let onSessionPersist: ((s: AuthSession) => Promise<void>) | null = null;
let onAuthFailure: (() => void) | null = null;

export function setSession(session: AuthSession | null) {
  memorySession = session;
}

export function getSession(): AuthSession | null {
  return memorySession;
}

export function setSessionPersistHandler(
  handler: ((s: AuthSession) => Promise<void>) | null
) {
  onSessionPersist = handler;
}

export function setOnAuthFailure(handler: (() => void) | null) {
  onAuthFailure = handler;
}

function applyAuthHeaders(
  headers: InternalAxiosRequestConfig["headers"],
  session: AuthSession | null = getSession()
): void {
  if (!headers) return;
  const token = session?.access_token?.trim();
  if (!token) {
    return;
  }
  const h = headers as Record<string, string>;
  h.Authorization = `Bearer ${token}`;
  if (session?.refresh_token) {
    h["X-Refresh-Token"] = session.refresh_token;
  }
}

export class ApiClientError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
  }
}

function unwrap<T>(data: unknown): T {
  const d = data as { ok?: boolean; error?: string };
  if (d && d.ok === false) {
    throw new Error(d.error || "Erro na API");
  }
  return data as T;
}

const TIMEOUT_DEFAULT_MS = 60_000;
const TIMEOUT_CHAT_MS = 120_000;
/** Voz: Gemini com áudio demora mais que texto. */
const TIMEOUT_VOICE_MS = 180_000;
const TIMEOUT_BOOTSTRAP_MS = 90_000;

const INTEGRITY_PATH_PREFIXES = [
  "chat/messages",
  "chat/voice",
  "chat/voice/stream",
  "voice/realtime/client-secret",
  "voice/realtime/webrtc",
  "voice/realtime/finish",
];

function needsPlayIntegrityHeader(url: string | undefined): boolean {
  const path = (url || "").replace(/^\//, "");
  return INTEGRITY_PATH_PREFIXES.some((p) => path.startsWith(p));
}

export const api: AxiosInstance = axios.create({
  baseURL: apiBase,
  timeout: TIMEOUT_DEFAULT_MS,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use(async (config) => {
  applyAuthHeaders(config.headers);
  if (needsPlayIntegrityHeader(config.url)) {
    const integrityToken = await getPlayIntegrityToken();
    if (integrityToken && config.headers) {
      const h = config.headers as Record<string, string>;
      h["X-Play-Integrity"] = integrityToken;
    }
  }
  // FormData precisa do boundary automático do browser (não application/json).
  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
    const h = config.headers as Record<string, unknown>;
    delete h["Content-Type"];
    delete h["content-type"];
  }
  return config;
});

type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean };

api.interceptors.response.use(
  (res) => res,
  async (err: AxiosError<ApiErr>) => {
    const original = err.config as RetryConfig | undefined;
    const status = err.response?.status;
    const session = getSession();

    if (
      status === 401 &&
      original &&
      !original._retry &&
      session?.refresh_token
    ) {
      original._retry = true;
      try {
        const next = await refreshSessionToken(session.refresh_token);
        setSession(next);
        if (onSessionPersist) {
          await onSessionPersist(next);
        }
        applyAuthHeaders(original.headers, next);
        return api(original);
      } catch {
        setSession(null);
        onAuthFailure?.();
      }
    } else if (status === 401) {
      setSession(null);
      onAuthFailure?.();
    }

    const timedOut =
      err.code === "ECONNABORTED" || err.code === "ETIMEDOUT";
    const isVoiceReq = Boolean(original?.url?.includes("chat/voice"));
    const networkFailed =
      !err.response &&
      (err.message === "Network Error" ||
        err.code === "ERR_NETWORK" ||
        err.code === "ECONNREFUSED");
    const webOrigin = getWebOrigin();
    const isProdApi = /^https:\/\//i.test(apiBase);
    const apiHint = apiBase.startsWith("http")
      ? apiBase.replace(/\/api\/v1\/?$/, "")
      : webOrigin || "http://SEU_IP:8081";
    const msg =
      err.response?.data?.error ||
      (timedOut
        ? isVoiceReq
          ? "O Gemini demorou mais de 2 minutos a ouvir o áudio. Grave só 3–5 segundos e tente outra vez, ou escreva em texto."
          : isProdApi
            ? "O servidor demorou demais (mensagens de voz demoram mais). Aguarde 10s e tente de novo; se persistir, use texto ou mensagem de voz mais curta."
            : "O servidor demorou demais (IA ou rede). Verifique se python flask_api.py está a correr e se EXPO_PUBLIC_API_URL aponta para o PC (telefone: use o IP da rede, não localhost). Tente de novo."
        : networkFailed
          ? isProdApi
            ? "Sem ligação ao servidor. Verifique sua internet e tente novamente."
            : `Sem ligação à API. Confirme: (1) python flask_api.py no PC, (2) Flask a correr na porta 5000, (3) no PC use ${webOrigin || "http://localhost:8081"} (não :5000 no browser). Telefone: mesma Wi‑Fi e ${apiHint}.`
          : err.message) ||
      "Não foi possível contactar o servidor. Verifique a internet e a URL da API.";
    reportApiFailure(original?.url, status, msg);
    return Promise.reject(new ApiClientError(msg, status));
  }
);

function parseDashboard(data: unknown): DashboardData {
  const body = unwrap<DashboardData>(data);
  return {
    health: body.health ?? null,
    me: body.me ?? null,
    access: body.access ?? null,
    reminders: body.reminders ?? [],
    agenda: body.agenda ?? [],
    shared_calendars: body.shared_calendars ?? [],
    messages: body.messages ?? [],
    chat_local_history: Boolean(body.chat_local_history),
  };
}

async function fetchDashboardLegacy(): Promise<DashboardData> {
  const healthReq = axios
    .get<HealthInfo>(`${apiBase}health`, { timeout: 8000 })
    .catch(() => null);

  const [healthRes, meRes, accessRes, remRes, agRes, chatRes] = await Promise.all([
    healthReq,
    api.get("me"),
    api.get("access"),
    api.get("reminders"),
    api.get("agenda"),
    api.get("chat/messages"),
  ]);

  const meBody = unwrap<MeData & { ok?: boolean }>(meRes.data);
  const accessBody = unwrap<AccessInfo & { ok?: boolean }>(accessRes.data);
  const remBody = unwrap<{ reminders: DashboardData["reminders"] }>(remRes.data);
  const agBody = unwrap<{ agenda: DashboardData["agenda"] }>(agRes.data);
  const chatBody = unwrap<{ messages: DashboardData["messages"] }>(chatRes.data);

  return {
    health: healthRes ? unwrap<HealthInfo>(healthRes.data) : null,
    me: meBody,
    access: accessBody,
    reminders: remBody.reminders ?? [],
    agenda: agBody.agenda ?? [],
    messages: chatBody.messages ?? [],
  };
}

function isNotFound(err: unknown): boolean {
  if (err instanceof ApiClientError && err.status === 404) return true;
  if (axios.isAxiosError(err) && err.response?.status === 404) return true;
  const msg = err instanceof Error ? err.message : "";
  return /\b404\b/.test(msg) || /not found/i.test(msg);
}

export async function fetchDashboard(): Promise<DashboardData> {
  try {
    const tz_offset_min = -new Date().getTimezoneOffset();
    const timezone =
      typeof Intl !== "undefined"
        ? Intl.DateTimeFormat().resolvedOptions().timeZone || ""
        : "";
    const { data } = await api.post(
      "app/bootstrap",
      { timezone, tz_offset_min },
      {
      timeout: TIMEOUT_BOOTSTRAP_MS,
      }
    );
    return parseDashboard(data);
  } catch (err) {
    if (isNotFound(err)) {
      return fetchDashboardLegacy();
    }
    throw err;
  }
}

function normalizeSession(raw: unknown): AuthSession {
  const s = (raw || {}) as Record<string, unknown>;
  const nested = (s.session || s) as Record<string, unknown>;
  const access =
    String(nested.access_token || nested.accessToken || "").trim();
  const refresh =
    String(nested.refresh_token || nested.refreshToken || "").trim();
  const userRaw = (nested.user || {}) as Record<string, unknown>;
  if (!access) {
    throw new Error("Resposta de login sem token de acesso.");
  }
  return {
    access_token: access,
    refresh_token: refresh,
    expires_at: (nested.expires_at as number) ?? null,
    user: {
      id: String(userRaw.id || ""),
      email: String(userRaw.email || ""),
    },
  };
}

export async function login(email: string, password: string): Promise<AuthSession> {
  const { data } = await api.post("auth/login", { email, password });
  const body = unwrap<{ session: AuthSession }>(data);
  const session = normalizeSession(body.session ?? body);
  setSession(session);
  return session;
}

export async function validateReferralCode(
  code: string
): Promise<{ valid: boolean; display_name?: string; code?: string }> {
  const { data } = await api.post("referrals/validate", {
    code: code.trim(),
  });
  const body = unwrap<{ valid: boolean; display_name?: string; code?: string }>(data);
  return body;
}

export async function signup(
  email: string,
  password: string,
  fullName?: string,
  referralCode?: string
): Promise<AuthSession | null> {
  const { data } = await api.post("auth/signup", {
    email,
    password,
    full_name: fullName || "",
    referral_code: (referralCode || "").trim(),
  });
  const body = unwrap<{ session: AuthSession; message?: string }>(data);
  if (body.session?.access_token || (body as { access_token?: string }).access_token) {
    const session = normalizeSession(body.session ?? body);
    setSession(session);
    return session;
  }
  return null;
}

export async function refreshSessionToken(
  refresh_token: string
): Promise<AuthSession> {
  const { data } = await axios.post(
    `${apiBase}auth/refresh`,
    { refresh_token },
    { timeout: 20000, headers: { "Content-Type": "application/json" } }
  );
  const body = unwrap<{ session: AuthSession }>(data);
  if (!body.session?.access_token) {
    throw new Error("Não foi possível renovar a sessão.");
  }
  return body.session;
}

export async function requestPasswordReset(email: string): Promise<string> {
  const { data } = await axios.post(
    `${apiBase}auth/forgot-password`,
    { email },
    { timeout: 20000, headers: { "Content-Type": "application/json" } }
  );
  const body = unwrap<{ message?: string }>(data);
  return body.message || "Se o e-mail existir, receberá instruções por e-mail.";
}

export type LegalDoc = "terms" | "privacy" | "refund";

export async function fetchPlansCatalog(): Promise<PlanCatalogItem[]> {
  const { data } = await axios.get(`${apiBase}plans`, { timeout: 15000 });
  const body = unwrap<{ plans: PlanCatalogItem[] }>(data);
  return body.plans ?? [];
}

export async function fetchLegalMarkdown(doc: LegalDoc): Promise<string> {
  const { data } = await axios.get(`${apiBase}legal/${doc}`, { timeout: 20000 });
  const body = unwrap<{ markdown: string }>(data);
  return body.markdown || "";
}

export async function deleteAgendaItem(agendaId: string): Promise<void> {
  await api.delete(`agenda/${agendaId}`);
}

export async function dismissReminder(reminderId: string): Promise<void> {
  await api.post(`reminders/${reminderId}/dismiss`);
}

export async function createPersonalReminder(payload: {
  title: string;
  scheduled_at: string;
  announce?: string;
}): Promise<Reminder> {
  const { data } = await api.post("reminders", payload);
  const body = unwrap<{ reminder: Reminder }>(data);
  if (!body.reminder?.id) {
    throw new Error("Não foi possível guardar na agenda pessoal.");
  }
  return body.reminder;
}

function sharedCalendarFriendlyError(err: unknown, fallback: string): string {
  if (err instanceof ApiClientError && err.status === 404) {
    return (
      "Agendas compartilhadas ainda não estão no servidor (API desatualizada). " +
      "Faça deploy do código novo no Railway e execute a migration SQL no Supabase."
    );
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

export async function fetchSharedCalendars(): Promise<SharedCalendar[]> {
  try {
    const { data } = await api.get("shared-calendars");
    const body = unwrap<{ shared_calendars: SharedCalendar[] }>(data);
    return body.shared_calendars ?? [];
  } catch (e) {
    throw new Error(sharedCalendarFriendlyError(e, "Erro ao carregar agendas."));
  }
}

export async function createSharedCalendar(name: string): Promise<SharedCalendar> {
  try {
    const { data } = await api.post("shared-calendars", { name });
    const body = unwrap<{ calendar: SharedCalendar }>(data);
    if (!body.calendar?.id) {
      throw new Error("Não foi possível criar a agenda compartilhada.");
    }
    return body.calendar;
  } catch (e) {
    throw new Error(sharedCalendarFriendlyError(e, "Não foi possível criar a agenda."));
  }
}

export async function fetchSharedCalendar(calendarId: string): Promise<SharedCalendar> {
  const { data } = await api.get(`shared-calendars/${calendarId}`);
  const body = unwrap<{ calendar: SharedCalendar }>(data);
  if (!body.calendar?.id) {
    throw new Error("Agenda não encontrada.");
  }
  return body.calendar;
}

export async function deleteSharedCalendar(calendarId: string): Promise<void> {
  try {
    await api.delete(`shared-calendars/${calendarId}`);
  } catch (e) {
    throw new Error(
      sharedCalendarFriendlyError(e, "Não foi possível apagar a agenda compartilhada.")
    );
  }
}

export async function addSharedCalendarMember(
  calendarId: string,
  email: string
): Promise<SharedCalendarMember> {
  const { data } = await api.post(`shared-calendars/${calendarId}/members`, {
    email,
  });
  const body = unwrap<{ member: SharedCalendarMember }>(data);
  return body.member;
}

export async function removeSharedCalendarMember(
  calendarId: string,
  memberId: string
): Promise<void> {
  await api.delete(`shared-calendars/${calendarId}/members/${memberId}`);
}

export async function createSharedCalendarEvent(
  calendarId: string,
  payload: { title: string; scheduled_at: string; announce?: string }
): Promise<SharedCalendarEvent> {
  const { data } = await api.post(`shared-calendars/${calendarId}/events`, payload);
  const body = unwrap<{ event: SharedCalendarEvent }>(data);
  if (!body.event?.id) {
    throw new Error("Não foi possível marcar a reunião.");
  }
  return body.event;
}

export async function dismissSharedCalendarEvent(
  calendarId: string,
  eventId: string
): Promise<void> {
  await api.post(`shared-calendars/${calendarId}/events/${eventId}/dismiss`);
}

/** Converte DD/MM/AAAA + HH:MM para ISO com fuso local. */
export function localDateTimeToIso(dateBr: string, timeBr: string): string | null {
  const dm = dateBr.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  const tm = timeBr.trim().match(/^(\d{1,2}):(\d{2})$/);
  if (!dm || !tm) return null;
  const day = Number(dm[1]);
  const month = Number(dm[2]) - 1;
  const year = Number(dm[3]);
  const hour = Number(tm[1]);
  const minute = Number(tm[2]);
  const d = new Date(year, month, day, hour, minute, 0, 0);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

export async function sendChatMessage(
  message: string,
  speak = true,
  history: ChatHistoryPayload = []
): Promise<SendChatResult> {
  const { data } = await api.post(
    "chat/messages",
    { message, speak, history },
    { timeout: TIMEOUT_CHAT_MS }
  );
  const body = unwrap<SendChatResult>(data);
  if (!body.reply) {
    throw new Error("A API não devolveu resposta do assistente.");
  }
  return body;
}

async function voiceAuthHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = {};
  const session = getSession();
  const token = session?.access_token?.trim();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
    if (session?.refresh_token) {
      headers["X-Refresh-Token"] = session.refresh_token;
    }
  }
  const integrityToken = await getPlayIntegrityToken();
  if (integrityToken) {
    headers["X-Play-Integrity"] = integrityToken;
  }
  return headers;
}

function appendVoiceFormFields(
  form: FormData,
  opts: {
    blob?: Blob;
    uri?: string;
    audioMime: string;
    speak?: boolean;
    history?: ChatHistoryPayload;
  }
): void {
  const audio_mime = opts.audioMime;
  const ext = audio_mime.includes("webm") ? "webm" : audio_mime.includes("wav") ? "wav" : "m4a";
  if (opts.blob) {
    form.append("audio", voiceUploadFile(opts.blob, audio_mime));
  } else if (opts.uri) {
    form.append("audio", {
      uri: opts.uri,
      name: `voice.${ext}`,
      type: audio_mime,
    } as unknown as Blob);
  }
  form.append("audio_mime", audio_mime);
  form.append("speak", opts.speak !== false ? "true" : "false");
  if (opts.history?.length) {
    form.append("history", JSON.stringify(opts.history));
  }
}

async function readVoiceNdjsonStream(
  response: Response,
  onDelta?: (chunk: string, full: string) => void
): Promise<SendChatResult> {
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("Streaming indisponível neste dispositivo.");
  }
  const decoder = new TextDecoder();
  let buffer = "";
  let full = "";
  let donePayload: SendChatResult | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const ev = JSON.parse(trimmed) as {
        type?: string;
        text?: string;
        error?: string;
        result?: SendChatResult;
      };
      if (ev.type === "delta" && ev.text) {
        full += ev.text;
        onDelta?.(ev.text, full);
      } else if (ev.type === "error") {
        throw new Error(ev.error || "Erro ao processar voz.");
      } else if (ev.type === "done" && ev.result) {
        donePayload = ev.result;
      }
    }
  }

  if (donePayload?.reply) {
    return donePayload;
  }
  if (full.trim()) {
    return { reply: full.trim() };
  }
  throw new Error("A API não devolveu resposta do assistente.");
}

function voiceUploadFile(blob: Blob, mime: string): Blob | File {
  const audio_mime = mime.includes("webm")
    ? "audio/webm"
    : mime.includes("mp4") || mime.includes("m4a")
      ? "audio/mp4"
      : mime.includes("wav")
        ? "audio/wav"
        : mime;
  const ext = audio_mime.includes("webm") ? "webm" : audio_mime.includes("wav") ? "wav" : "m4a";
  if (typeof File !== "undefined") {
    return new File([blob], `voice.${ext}`, { type: audio_mime });
  }
  return blob;
}

/** Envio de voz (browser) — ficheiro + endpoint /chat/voice (axios, timeout 90s). */
export async function sendChatVoiceBlob(opts: {
  blob: Blob;
  audioMime?: string;
  speak?: boolean;
  history?: ChatHistoryPayload;
}): Promise<SendChatResult> {
  if (!opts.blob || opts.blob.size < 256) {
    throw new Error("Gravação demasiado curta. Fale pelo menos 1 segundo.");
  }

  const mime = (opts.audioMime || opts.blob.type || "audio/webm").toLowerCase();
  const audio_mime = mime.includes("webm")
    ? "audio/webm"
    : mime.includes("mp4") || mime.includes("m4a")
      ? "audio/mp4"
      : mime.includes("wav")
        ? "audio/wav"
        : mime;

  const form = new FormData();
  appendVoiceFormFields(form, {
    blob: opts.blob,
    audioMime: audio_mime,
    speak: opts.speak,
    history: opts.history,
  });

  const { data } = await api.post("chat/voice", form, {
    timeout: 150_000,
    maxBodyLength: Infinity,
    maxContentLength: Infinity,
  });
  const body = unwrap<SendChatResult>(data);
  if (!body.reply) {
    throw new Error("A API não devolveu resposta do assistente.");
  }
  return body;
}

/** Voz com streaming — texto aparece antes do áudio (estilo ChatGPT). */
export async function sendChatVoiceBlobStream(opts: {
  blob: Blob;
  audioMime?: string;
  speak?: boolean;
  history?: ChatHistoryPayload;
  onDelta?: (chunk: string, full: string) => void;
}): Promise<SendChatResult> {
  if (!opts.blob || opts.blob.size < 256) {
    throw new Error("Gravação demasiado curta. Fale pelo menos 1 segundo.");
  }

  const mime = (opts.audioMime || opts.blob.type || "audio/webm").toLowerCase();
  const audio_mime = mime.includes("webm")
    ? "audio/webm"
    : mime.includes("mp4") || mime.includes("m4a")
      ? "audio/mp4"
      : mime.includes("wav")
        ? "audio/wav"
        : mime;

  const form = new FormData();
  appendVoiceFormFields(form, {
    blob: opts.blob,
    audioMime: audio_mime,
    speak: opts.speak,
    history: opts.history,
  });

  const streamUrl = `${API_V1.replace(/\/$/, "")}/chat/voice/stream`;
  try {
    const headers = await voiceAuthHeaders();
    const res = await fetch(streamUrl, { method: "POST", headers, body: form });
    if (!res.ok) {
      let msg = `Erro ${res.status}`;
      try {
        const j = (await res.json()) as { error?: string };
        if (j.error) msg = j.error;
      } catch {
        /* ignore */
      }
      throw new Error(msg);
    }
    return await readVoiceNdjsonStream(res, opts.onDelta);
  } catch (e) {
    if (e instanceof Error && e.message.includes("Streaming indisponível")) {
      return sendChatVoiceBlob(opts);
    }
    throw e instanceof Error ? e : new Error("Erro ao enviar voz.");
  }
}

/** Voz nativa (URI) com streaming NDJSON. */
export async function sendChatVoiceUriStream(opts: {
  uri: string;
  audioMime?: string;
  speak?: boolean;
  history?: ChatHistoryPayload;
  onDelta?: (chunk: string, full: string) => void;
}): Promise<SendChatResult> {
  const mime = (opts.audioMime || "audio/mp4").toLowerCase();
  const audio_mime = mime.includes("webm")
    ? "audio/webm"
    : mime.includes("mp4") || mime.includes("m4a")
      ? "audio/mp4"
      : mime.includes("wav")
        ? "audio/wav"
        : mime;

  const form = new FormData();
  appendVoiceFormFields(form, {
    uri: opts.uri,
    audioMime: audio_mime,
    speak: opts.speak,
    history: opts.history,
  });

  const streamUrl = `${API_V1.replace(/\/$/, "")}/chat/voice/stream`;
  try {
    const headers = await voiceAuthHeaders();
    const res = await fetch(streamUrl, { method: "POST", headers, body: form });
    if (!res.ok) {
      throw new Error(`Erro ${res.status}`);
    }
    return await readVoiceNdjsonStream(res, opts.onDelta);
  } catch {
    return sendChatVoiceMessage({
      audioBase64: await FileSystem.readAsStringAsync(opts.uri, {
        encoding: FileSystem.EncodingType.Base64,
      }),
      audioMime: audio_mime,
      speak: opts.speak,
      history: opts.history,
    });
  }
}

export async function sendChatVoiceMessage(opts: {
  audioBase64: string;
  audioMime?: string;
  speak?: boolean;
  history?: ChatHistoryPayload;
}): Promise<SendChatResult> {
  const audioBase64 = (opts.audioBase64 || "").trim();
  if (!audioBase64 || audioBase64.length < 400) {
    throw new Error("Gravação demasiado curta. Fale pelo menos 2 segundos.");
  }
  const mime = (opts.audioMime || "audio/webm").toLowerCase();
  const audio_mime =
    mime.includes("webm")
      ? "audio/webm"
      : mime.includes("mp4") || mime.includes("m4a")
        ? "audio/mp4"
        : mime.includes("wav")
          ? "audio/wav"
          : opts.audioMime || "audio/webm";
  const { data } = await api.post(
    "chat/messages",
    {
      message: "",
      audio_base64: audioBase64,
      audio_mime,
      speak: opts.speak !== false,
      history: opts.history ?? [],
    },
    {
      timeout: TIMEOUT_VOICE_MS,
      maxBodyLength: Infinity,
      maxContentLength: Infinity,
    }
  );
  const body = unwrap<SendChatResult>(data);
  if (!body.reply) {
    throw new Error("A API não devolveu resposta do assistente.");
  }
  return body;
}

export async function fetchTtsAudio(
  text: string,
  voiceId?: string,
  avatarId?: string
): Promise<{ audio_base64: string; mime: string }> {
  const resolvedVoice = resolveSpeechVoiceId(voiceId, avatarId);
  const { data } = await api.post(
    "tts",
    {
      text,
      voice_id: resolvedVoice,
      avatar_id: avatarId?.trim() || undefined,
    },
    { timeout: TIMEOUT_CHAT_MS }
  );
  const body = unwrap<{ audio_base64: string; mime: string; voice_id?: string }>(data);
  if (!body.audio_base64?.trim()) {
    throw new Error("O servidor devolveu áudio vazio.");
  }
  return { audio_base64: body.audio_base64, mime: body.mime || "audio/mpeg" };
}

export async function updatePersonaPreset(
  preset: "male" | "female"
): Promise<{ avatar_id: string; voice_id: string }> {
  const { data } = await api.put("persona", { preset });
  const body = unwrap<{
    saved?: boolean;
    avatar_id?: string;
    voice_id?: string;
  }>(data);
  const avatar_id = String(body.avatar_id || (preset === "male" ? "m1" : "f1"));
  const voice_id = String(body.voice_id || (preset === "male" ? "vm1" : "vf1"));
  if (body.saved === false) {
    throw new Error("O servidor não guardou a escolha do assistente.");
  }
  if (!avatar_id || !voice_id) {
    throw new Error("Resposta inválida ao guardar assistente.");
  }
  return { avatar_id, voice_id };
}

export async function savePersonaChoice(
  choice: { avatar_id: string; voice_id: string }
): Promise<{ avatar_id: string; voice_id: string }> {
  const { data } = await api.put("persona", {
    avatar_id: choice.avatar_id,
    voice_id: choice.voice_id,
  });
  const body = unwrap<{
    saved?: boolean;
    avatar_id?: string;
    voice_id?: string;
  }>(data);
  const avatar_id = String(body.avatar_id || choice.avatar_id);
  const voice_id = String(body.voice_id || choice.voice_id);
  if (body.saved === false) {
    throw new Error("O servidor não guardou a escolha do assistente.");
  }
  return { avatar_id, voice_id };
}

export async function updatePersona(
  avatarId: string,
  voiceId: string
): Promise<{ avatar_id: string; voice_id: string }> {
  const { data } = await api.put("persona", {
    avatar_id: avatarId,
    voice_id: voiceId,
  });
  const body = unwrap<{ avatar_id: string; voice_id: string }>(data);
  return { avatar_id: body.avatar_id, voice_id: body.voice_id };
}

export async function logoutApi(): Promise<void> {
  try {
    await api.post("auth/logout");
  } catch {
    /* ignore */
  }
}

export { STORAGE_KEY };
