import axios, { AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from "axios";
import { API_V1 } from "@/constants/config";
import { resolveSpeechVoiceId } from "@/constants/personas";
import type {
  AccessInfo,
  ApiErr,
  AuthSession,
  DashboardData,
  HealthInfo,
  MeData,
  LaunchPlanOffer,
  PlanCatalogItem,
  SendChatResult,
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
const TIMEOUT_BOOTSTRAP_MS = 90_000;

export const api: AxiosInstance = axios.create({
  baseURL: apiBase,
  timeout: TIMEOUT_DEFAULT_MS,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  applyAuthHeaders(config.headers);
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
    const networkFailed =
      !err.response &&
      (err.message === "Network Error" ||
        err.code === "ERR_NETWORK" ||
        err.code === "ECONNREFUSED");
    const webOrigin =
      typeof window !== "undefined" ? window.location.origin : "";
    const isProdApi = /^https:\/\//i.test(apiBase);
    const apiHint = apiBase.startsWith("http")
      ? apiBase.replace(/\/api\/v1\/?$/, "")
      : webOrigin || "http://SEU_IP:8081";
    const msg =
      err.response?.data?.error ||
      (timedOut
        ? isProdApi
          ? "O servidor demorou demais para responder. Tente novamente em instantes."
          : "O servidor demorou demais (IA ou rede). Verifique se python flask_api.py está a correr e se EXPO_PUBLIC_API_URL aponta para o PC (telefone: use o IP da rede, não localhost). Tente de novo."
        : networkFailed
          ? isProdApi
            ? "Sem ligação ao servidor. Verifique sua internet e tente novamente."
            : `Sem ligação à API. Confirme: (1) python flask_api.py no PC, (2) mesma Wi‑Fi, (3) no telefone abra ${apiHint} (não use :5000). No PC: http://localhost:8081.`
          : err.message) ||
      "Não foi possível contactar o servidor. Verifique a internet e a URL da API.";
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

export async function signup(
  email: string,
  password: string,
  fullName?: string
): Promise<AuthSession | null> {
  const { data } = await api.post("auth/signup", {
    email,
    password,
    full_name: fullName || "",
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

export async function fetchPlansCatalog(): Promise<{
  plans: PlanCatalogItem[];
  launchOffer: LaunchPlanOffer | null;
}> {
  const { data } = await axios.get(`${apiBase}plans`, { timeout: 15000 });
  const body = unwrap<{
    plans: PlanCatalogItem[];
    launch_offer?: LaunchPlanOffer | null;
  }>(data);
  return {
    plans: body.plans ?? [],
    launchOffer: body.launch_offer ?? null,
  };
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

export async function sendChatMessage(
  message: string,
  speak = true
): Promise<SendChatResult> {
  const { data } = await api.post(
    "chat/messages",
    { message, speak: speak },
    { timeout: TIMEOUT_CHAT_MS }
  );
  const body = unwrap<SendChatResult>(data);
  if (!body.reply) {
    throw new Error("A API não devolveu resposta do assistente.");
  }
  return body;
}

/** Envio de voz no browser (Safari) — ficheiro binário, sem base64 no JSON. */
export async function sendChatVoiceBlob(opts: {
  blob: Blob;
  speak?: boolean;
}): Promise<SendChatResult> {
  if (!opts.blob || opts.blob.size < 256) {
    throw new Error("Gravação demasiado curta. Fale pelo menos 1 segundo.");
  }
  const mime = (opts.blob.type || "audio/mp4").toLowerCase();
  const ext = mime.includes("webm") ? "webm" : "m4a";
  const form = new FormData();
  form.append("audio", opts.blob, `voice.${ext}`);
  form.append("message", "");
  form.append("audio_mime", mime.includes("mp4") || mime.includes("m4a") ? "audio/mp4" : mime);
  form.append("speak", opts.speak !== false ? "true" : "false");

  const { data } = await api.post("chat/messages", form, {
    timeout: TIMEOUT_CHAT_MS,
  });
  const body = unwrap<SendChatResult>(data);
  if (!body.reply) {
    throw new Error("A API não devolveu resposta do assistente.");
  }
  return body;
}

export async function sendChatVoiceMessage(opts: {
  audioBase64: string;
  audioMime?: string;
  speak?: boolean;
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
    },
    { timeout: TIMEOUT_CHAT_MS }
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
