import axios, { AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from "axios";
import * as FileSystem from "expo-file-system";
import { Platform } from "react-native";
import { API_V1 } from "@/constants/config";
import { normalizeAccessInfo } from "@/constants/planLimits";
import { resolveSpeechVoiceId } from "@/constants/personas";
import { getPlayIntegrityToken } from "@/security/playIntegrity";
import { sessionNeedsRefresh } from "@/storage/sessionRefresh";
import type {
  AccessInfo,
  ApiErr,
  AuthSession,
  DashboardData,
  HealthInfo,
  PublicHealthInfo,
  MeData,
  LaunchPlanOffer,
  PlanCatalogItem,
  ReferralPlanOffer,
  AgendaDraft,
  ChatHistoryPayload,
  NightDumpResult,
  SendChatResult,
  SharedCalendar,
  SharedCalendarMember,
  ShoppingListItem,
  StreakInfo,
  WellnessJourney,
  DailyCareInfo,
} from "./types";

const STORAGE_KEY = "ego_auth_session";
export const LAST_EMAIL_KEY = "ego_last_email";

function deviceTimezonePayload(): { timezone: string; tz_offset_min: number } {
  const tz_offset_min = -new Date().getTimezoneOffset();
  const timezone =
    typeof Intl !== "undefined"
      ? Intl.DateTimeFormat().resolvedOptions().timeZone || ""
      : "";
  return { timezone, tz_offset_min };
}

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

export const DEFAULT_UPDATING_MESSAGE =
  "Estamos atualizando o servidor. Tente de novo em instantes.";

export async function fetchPublicHealth(): Promise<PublicHealthInfo | null> {
  try {
    const { data } = await axios.get(`${apiBase}health`, { timeout: 8000 });
    return unwrap<PublicHealthInfo>(data);
  } catch {
    return null;
  }
}

const TIMEOUT_DEFAULT_MS = 60_000;
const TIMEOUT_CHAT_MS = 120_000;
const TIMEOUT_BOOTSTRAP_MS = 90_000;

const INTEGRITY_ROUTES = [
  "chat/messages",
  "tts",
  "night-dump",
  "voice/realtime",
] as const;

function routeNeedsIntegrity(url: string | undefined, method: string | undefined): boolean {
  if (!url || (method || "get").toLowerCase() !== "post") return false;
  const path = url.split("?")[0] || "";
  return INTEGRITY_ROUTES.some((segment) => path.includes(segment));
}

export const api: AxiosInstance = axios.create({
  baseURL: apiBase,
  timeout: TIMEOUT_DEFAULT_MS,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use(async (config) => {
  applyAuthHeaders(config.headers);
  const h = config.headers as Record<string, string>;
  h["X-EGO-Platform"] = Platform.OS;
  if (routeNeedsIntegrity(config.url, config.method)) {
    const token = await Promise.race([
      getPlayIntegrityToken(),
      new Promise<null>((resolve) => setTimeout(() => resolve(null), 800)),
    ]);
    if (token) {
      h["X-Play-Integrity"] = token;
    }
  }
  // FormData precisa do boundary automático do browser (não application/json).
  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
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
        let next: AuthSession;
        try {
          next = await refreshSessionToken(session.refresh_token, session);
        } catch (firstErr) {
          const ax0 = firstErr as AxiosError;
          const retryable =
            !ax0.response ||
            ax0.code === "ERR_NETWORK" ||
            ax0.code === "ECONNABORTED" ||
            ax0.code === "ETIMEDOUT" ||
            (typeof ax0.response?.status === "number" &&
              ax0.response.status >= 500);
          if (!retryable) throw firstErr;
          await new Promise((r) => setTimeout(r, 400));
          next = await refreshSessionToken(session.refresh_token, session);
        }
        setSession(next);
        if (onSessionPersist) {
          await onSessionPersist(next);
        }
        applyAuthHeaders(original.headers, next);
        return api(original);
      } catch (refreshErr) {
        const ax = refreshErr as AxiosError;
        const refreshStatus = ax.response?.status;
        const networkish =
          !ax.response ||
          ax.code === "ERR_NETWORK" ||
          ax.code === "ECONNABORTED" ||
          ax.code === "ETIMEDOUT" ||
          (typeof refreshStatus === "number" && refreshStatus >= 500);
        const refreshInvalid =
          refreshStatus === 401 ||
          refreshStatus === 403 ||
          refreshStatus === 400;
        if (refreshInvalid || (!networkish && refreshStatus)) {
          setSession(null);
          onAuthFailure?.();
        }
      }
    } else if (status === 401 && !session?.refresh_token) {
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
    access: normalizeAccessInfo(body.access ?? null),
    reminders: body.reminders ?? [],
    agenda: body.agenda ?? [],
    agenda_drafts: body.agenda_drafts ?? [],
    shopping_orphans: body.shopping_orphans ?? [],
    delegation_requests: body.delegation_requests ?? [],
    streak: body.streak ?? { current: 0, longest: 0, active_today: false, at_risk: false },
    wellness_journey: body.wellness_journey,
    daily_care: body.daily_care,
    shared_calendars: body.shared_calendars ?? [],
    pending_calendar_invites: body.pending_calendar_invites ?? [],
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
    access: normalizeAccessInfo(accessBody),
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
    const { timezone, tz_offset_min } = deviceTimezonePayload();
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

export async function loadLastLoginEmail(): Promise<string> {
  try {
    const { getSecureItem } = await import("@/storage/sessionStorage");
    const raw = await getSecureItem(LAST_EMAIL_KEY);
    return (raw || "").trim();
  } catch {
    return "";
  }
}

export async function saveLastLoginEmail(email: string): Promise<void> {
  const trimmed = email.trim();
  try {
    const { saveSecureItem, deleteSecureItem } = await import("@/storage/sessionStorage");
    if (trimmed) {
      await saveSecureItem(LAST_EMAIL_KEY, trimmed);
    } else {
      await deleteSecureItem(LAST_EMAIL_KEY);
    }
  } catch {
    /* ignore */
  }
}

export type ReferralValidateResult = {
  valid: boolean;
  code?: string;
  display_name?: string;
  error?: string | null;
};

export async function validateReferralCode(
  code: string
): Promise<ReferralValidateResult> {
  const trimmed = code.trim();
  if (trimmed.length < 3) {
    return { valid: false, error: null };
  }
  const { data } = await axios.get(`${apiBase}referrals/validate`, {
    params: { code: trimmed },
    timeout: 15000,
  });
  const body = unwrap<ReferralValidateResult>(data);
  return {
    valid: Boolean(body.valid),
    code: body.code,
    display_name: body.display_name,
    error: body.error ?? null,
  };
}

export async function updateProfilePhone(phone: string): Promise<{ phone: string }> {
  const { data } = await api.patch("profile", { phone: phone.trim() });
  const body = unwrap<{ profile?: { phone?: string } }>(data);
  const saved =
    typeof body.profile?.phone === "string" ? body.profile.phone.trim() : "";
  if (!saved) {
    throw new Error(
      "Não foi possível confirmar o telefone. Tente de novo ou use outro número."
    );
  }
  return { phone: saved };
}

export async function signup(
  email: string,
  password: string,
  fullName?: string,
  phone?: string,
  referralCode?: string
): Promise<AuthSession | null> {
  const { data } = await api.post("auth/signup", {
    email,
    password,
    full_name: fullName || "",
    phone: phone?.trim() || "",
    referral_code: referralCode?.trim() || "",
  });
  const body = unwrap<{ session: AuthSession | null; message?: string }>(data);
  if (body.session?.access_token || (body as { access_token?: string }).access_token) {
    const session = normalizeSession(body.session ?? body);
    setSession(session);
    return session;
  }
  return null;
}

export type SignupCheckResult = {
  ok: boolean;
  reason?: string;
  message?: string;
  masked_email?: string;
  action?: "signup" | "login" | "forgot_password";
};

export async function checkSignupEligibility(
  email: string,
  phone: string
): Promise<SignupCheckResult> {
  const { data } = await axios.post(
    `${apiBase}auth/signup-check`,
    { email: email.trim(), phone: phone.trim() },
    { timeout: 20000, headers: { "Content-Type": "application/json" } }
  );
  const body = data as SignupCheckResult & { ok?: boolean; error?: string };
  // API devolve ok:false + message (e-mail/telefone já usado) — não é erro de transporte
  if (body.reason || typeof body.message === "string") {
    return {
      ok: Boolean(body.ok),
      reason: body.reason,
      message: body.message,
      masked_email: body.masked_email,
      action: body.action,
    };
  }
  if (body.ok === false) {
    throw new Error(body.error || "Não foi possível verificar o cadastro.");
  }
  return {
    ok: true,
    reason: body.reason,
    message: body.message,
    masked_email: body.masked_email,
    action: body.action,
  };
}

export async function refreshSessionToken(
  refresh_token: string,
  prior?: AuthSession | null
): Promise<AuthSession> {
  const { data } = await axios.post(
    `${apiBase}auth/refresh`,
    { refresh_token },
    { timeout: 20000, headers: { "Content-Type": "application/json" } }
  );
  const body = unwrap<{ session: AuthSession }>(data);
  const session = normalizeSession(body.session ?? body);
  return {
    ...session,
    refresh_token: session.refresh_token || prior?.refresh_token || refresh_token,
    user: session.user?.id ? session.user : prior?.user ?? session.user,
    expires_at: session.expires_at ?? prior?.expires_at ?? null,
  };
}

export async function requestPasswordReset(email: string): Promise<string> {
  const { data } = await axios.post(
    `${apiBase}auth/forgot-password`,
    { email },
    { timeout: 20000, headers: { "Content-Type": "application/json" } }
  );
  const body = unwrap<{ message?: string }>(data);
  return body.message || "Se o e-mail existir, receberá um link para criar nova senha.";
}

export async function completePasswordReset(
  access_token: string,
  refresh_token: string,
  password: string
): Promise<AuthSession> {
  const { data } = await axios.post(
    `${apiBase}auth/reset-password`,
    { access_token, refresh_token, password },
    { timeout: 20000, headers: { "Content-Type": "application/json" } }
  );
  const body = unwrap<{ session: AuthSession }>(data);
  const session = normalizeSession(body.session ?? body);
  if (!session.access_token) {
    throw new Error("Não foi possível confirmar a nova senha.");
  }
  setSession(session);
  return session;
}

export type LegalDoc = "terms" | "privacy" | "refund";

export async function fetchPlansCatalog(): Promise<{
  plans: PlanCatalogItem[];
  launchOffer: LaunchPlanOffer | null;
  referralOffer: ReferralPlanOffer | null;
}> {
  const { data } = await api.get("plans", { timeout: 15000 });
  const body = unwrap<{
    plans: PlanCatalogItem[];
    launch_offer?: LaunchPlanOffer | null;
    referral_offer?: ReferralPlanOffer | null;
  }>(data);
  return {
    plans: body.plans ?? [],
    launchOffer: body.launch_offer ?? null,
    referralOffer: body.referral_offer ?? null,
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

export async function createReminder(payload: {
  title: string;
  scheduled_at: string;
  announce?: string;
}): Promise<WellnessJourney | null> {
  const { data } = await api.post("reminders", payload);
  const body = unwrap<{ wellness_journey?: WellnessJourney }>(data);
  return body.wellness_journey ?? null;
}

export async function submitNightDumpText(text: string): Promise<NightDumpResult> {
  await ensureFreshSessionForPost();
  const { data } = await api.post(
    "night-dump",
    { text: text.trim(), ...deviceTimezonePayload() },
    { timeout: TIMEOUT_CHAT_MS }
  );
  return unwrap<NightDumpResult>(data);
}

export async function submitNightDumpBlob(blob: Blob): Promise<NightDumpResult> {
  if (!blob || blob.size < 256) {
    throw new Error("Gravação demasiado curta. Fale pelo menos 1 segundo.");
  }
  const mime = (blob.type || "audio/mp4").toLowerCase();
  const ext = mime.includes("webm") ? "webm" : "m4a";
  const form = new FormData();
  form.append("audio", blob, `night-dump.${ext}`);
  form.append("audio_mime", mime.includes("mp4") || mime.includes("m4a") ? "audio/mp4" : mime);
  const tz = deviceTimezonePayload();
  form.append("timezone", tz.timezone);
  form.append("tz_offset_min", String(tz.tz_offset_min));
  const authFields = voiceUploadAuthFormFields();
  if (authFields.access_token) form.append("access_token", authFields.access_token);
  if (authFields.refresh_token) form.append("refresh_token", authFields.refresh_token);
  await ensureFreshSessionForPost();
  const { data } = await api.post("night-dump", form, { timeout: TIMEOUT_CHAT_MS });
  return unwrap<NightDumpResult>(data);
}

async function submitNightDumpBase64FromUri(opts: {
  uri: string;
  audioMime?: string;
}): Promise<NightDumpResult> {
  const uri = (opts.uri || "").trim();
  if (!uri) throw new Error("Gravação vazia.");
  const audio_mime = normalizeVoiceMime(opts.audioMime);
  const audio_base64 = await FileSystem.readAsStringAsync(uri, {
    encoding: FileSystem.EncodingType.Base64,
  });
  await ensureFreshSessionForPost();
  const { data } = await api.post(
    "night-dump",
    { audio_base64, audio_mime, ...deviceTimezonePayload() },
    { timeout: TIMEOUT_CHAT_MS }
  );
  return unwrap<NightDumpResult>(data);
}

export async function submitNightDumpFromUri(opts: {
  uri: string;
  audioMime?: string;
}): Promise<NightDumpResult> {
  const uri = (opts.uri || "").trim();
  if (!uri) throw new Error("Gravação vazia.");
  const audio_mime = normalizeVoiceMime(opts.audioMime);
  if (Platform.OS !== "web") {
    await ensureFreshSessionForPost();
    try {
      const base = API_V1.endsWith("/") ? API_V1 : `${API_V1}/`;
      const url = `${base}night-dump`;
      const res = await FileSystem.uploadAsync(url, uri, {
        httpMethod: "POST",
        uploadType: FileSystem.FileSystemUploadType.MULTIPART,
        fieldName: "audio",
        mimeType: audio_mime,
        headers: await buildVoiceUploadHeaders(),
        parameters: {
          audio_mime,
          ...voiceUploadAuthFormFields(),
          ...Object.fromEntries(
            Object.entries(deviceTimezonePayload()).map(([k, v]) => [k, String(v)])
          ),
        },
      });
      if (res.status < 200 || res.status >= 300) {
        let detail = `Erro ${res.status} ao enviar desabafo.`;
        try {
          const parsed = JSON.parse(res.body) as { error?: string };
          if (parsed.error) detail = parsed.error;
        } catch {
          /* ignore */
        }
        throw new ApiClientError(detail, res.status);
      }
      return unwrap<NightDumpResult>(JSON.parse(res.body));
    } catch (nativeErr) {
      if (Platform.OS === "android") {
        try {
          return await submitNightDumpBase64FromUri(opts);
        } catch {
          throw nativeErr;
        }
      }
      throw nativeErr;
    }
  }
  const audioBase64 = await FileSystem.readAsStringAsync(uri, {
    encoding: FileSystem.EncodingType.Base64,
  });
  const { data } = await api.post(
    "night-dump",
    { audio_base64: audioBase64, audio_mime, ...deviceTimezonePayload() },
    { timeout: TIMEOUT_CHAT_MS }
  );
  return unwrap<NightDumpResult>(data);
}

export async function fetchPendingAgendaDrafts(): Promise<AgendaDraft[]> {
  const { data } = await api.get("agenda-drafts/pending");
  const body = unwrap<{ drafts: AgendaDraft[] }>(data);
  return body.drafts ?? [];
}

export async function confirmAgendaDraft(
  draftId: string,
  itemIndices?: number[]
): Promise<{ confirmed: boolean; errors?: string[]; shared_events?: unknown[] }> {
  const { data } = await api.post(`agenda-drafts/${draftId}/confirm`, {
    item_indices: itemIndices,
  });
  return unwrap(data);
}

export async function dismissAgendaDraft(draftId: string): Promise<void> {
  await api.post(`agenda-drafts/${draftId}/dismiss`);
}

export async function dismissAgendaDraftItem(
  draftId: string,
  itemIndex: number
): Promise<void> {
  await api.post(`agenda-drafts/${draftId}/items/${itemIndex}/dismiss`);
}

export async function confirmDelegationRequest(
  requestId: string
): Promise<{ confirmed: boolean }> {
  const { data } = await api.post(`delegation-requests/${requestId}/confirm`);
  return unwrap(data);
}

export async function dismissDelegationRequest(requestId: string): Promise<void> {
  await api.post(`delegation-requests/${requestId}/dismiss`);
}

export async function recordStreakActivity(
  source: "habit" | "night_dump" | "draft_confirm" | "delegation_confirm" = "habit"
): Promise<{ streak: StreakInfo; wellness_journey?: WellnessJourney }> {
  const { data } = await api.post("streaks/activity", { source });
  const body = unwrap<{ streak: StreakInfo; wellness_journey?: WellnessJourney }>(data);
  return {
    streak: body.streak ?? { current: 0, longest: 0 },
    wellness_journey: body.wellness_journey,
  };
}

export async function completeWellnessJourneyStep(
  step: "chat" | "voice" | "habit" | "reminder" | "night_dump" | "draft_confirm" | "invite"
): Promise<WellnessJourney | null> {
  try {
    const { data } = await api.post("wellness-journey/step", { step });
    const body = unwrap<{ wellness_journey: WellnessJourney }>(data);
    return body.wellness_journey ?? null;
  } catch {
    return null;
  }
}

export async function dismissWellnessLevelUp(): Promise<WellnessJourney | null> {
  try {
    const { data } = await api.post("wellness-journey/dismiss-level-up");
    const body = unwrap<{ wellness_journey: WellnessJourney }>(data);
    return body.wellness_journey ?? null;
  } catch {
    return null;
  }
}

export async function purchaseCompanionEggColor(
  colorId: string
): Promise<WellnessJourney | null> {
  try {
    const { data } = await api.post("wellness-journey/shop", { color: colorId });
    const body = unwrap<{ wellness_journey: WellnessJourney }>(data);
    return body.wellness_journey ?? null;
  } catch {
    return null;
  }
}

export async function submitDailyCareCheckin(moodKey: string): Promise<{
  daily_care: DailyCareInfo;
  wellness_journey?: WellnessJourney;
} | null> {
  try {
    const { data } = await api.post("daily-care/checkin", { mood: moodKey });
    const body = unwrap<{ daily_care: DailyCareInfo; wellness_journey?: WellnessJourney }>(data);
    if (!body.daily_care) return null;
    return body;
  } catch {
    return null;
  }
}

export async function submitDailyCareGoal(goalKey: string): Promise<{ daily_care: DailyCareInfo } | null> {
  try {
    const { data } = await api.post("daily-care/goal", { goal: goalKey });
    const body = unwrap<{ daily_care: DailyCareInfo }>(data);
    if (!body.daily_care) return null;
    return body;
  } catch {
    return null;
  }
}

export async function purchaseDailyCareShopItem(
  itemId: string
): Promise<{ daily_care: DailyCareInfo } | null> {
  try {
    const { data } = await api.post("daily-care/shop", { item: itemId });
    const body = unwrap<{ daily_care: DailyCareInfo }>(data);
    if (!body.daily_care) return null;
    return body;
  } catch {
    return null;
  }
}

export async function createShoppingItem(payload: {
  title: string;
  reminder_id?: string | null;
  category?: string;
}): Promise<ShoppingListItem> {
  const { data } = await api.post("shopping-list", payload);
  const body = unwrap<{ item: ShoppingListItem }>(data);
  if (!body.item) throw new Error("Item não devolvido pelo servidor.");
  return body.item;
}

export async function patchShoppingItem(
  itemId: string,
  patch: { done?: boolean; title?: string }
): Promise<void> {
  await api.patch(`shopping-list/${itemId}`, patch);
}

export async function deleteShoppingItem(itemId: string): Promise<void> {
  await api.delete(`shopping-list/${itemId}`);
}

export async function createAgendaItem(payload: {
  titulo: string;
  horario: string;
  dias_da_semana: string;
}): Promise<WellnessJourney | null> {
  const { data } = await api.post("agenda", payload);
  const body = unwrap<{ wellness_journey?: WellnessJourney }>(data);
  return body.wellness_journey ?? null;
}

export async function createSharedCalendar(name: string): Promise<SharedCalendar> {
  const { data } = await api.post("shared-calendars", { name: name.trim() });
  const body = unwrap<{ calendar: SharedCalendar }>(data);
  if (!body.calendar) throw new Error("Agenda não devolvida pelo servidor.");
  return body.calendar;
}

export async function fetchAccessInfo(): Promise<AccessInfo> {
  const { data } = await api.get("access", { timeout: TIMEOUT_DEFAULT_MS });
  const body = unwrap<AccessInfo & { ok?: boolean }>(data);
  return normalizeAccessInfo(body) ?? body;
}

export async function sendChatMessage(
  message: string,
  speak = true,
  history?: ChatHistoryPayload
): Promise<SendChatResult> {
  const { data } = await api.post(
    "chat/messages",
    { message, speak: speak, history: history ?? [], ...deviceTimezonePayload() },
    { timeout: TIMEOUT_CHAT_MS }
  );
  const body = unwrap<SendChatResult>(data);
  if (!body.reply) {
    throw new Error("A API não devolveu resposta do assistente.");
  }
  return body;
}

function normalizeVoiceMime(mime?: string): string {
  const m = (mime || "audio/mp4").toLowerCase();
  if (m.includes("webm")) return "audio/webm";
  if (m.includes("mp4") || m.includes("m4a")) return "audio/mp4";
  if (m.includes("wav")) return "audio/wav";
  return mime || "audio/mp4";
}

const VOICE_SEND_TIMEOUT_MS = 90_000;

function withVoiceSendTimeout<T>(promise: Promise<T>, label = "Envio de voz"): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) => {
      setTimeout(
        () => reject(new Error(`${label} demorou demais. Tente de novo.`)),
        VOICE_SEND_TIMEOUT_MS
      );
    }),
  ]);
}

/** Cópia para cache evita URI temporária inválida após parar a gravação (iOS + Android). */
async function stabilizeVoiceUri(uri: string): Promise<string> {
  const src = (uri || "").trim();
  if (!src || Platform.OS === "web") return src;
  const dir = FileSystem.cacheDirectory;
  if (!dir) return src;
  const dest = `${dir}ego_voice_${Date.now()}.m4a`;
  try {
    await FileSystem.copyAsync({ from: src, to: dest });
    return dest;
  } catch {
    return src;
  }
}

async function readVoiceBase64FromUri(uri: string): Promise<string> {
  const stable = await stabilizeVoiceUri(uri);
  return withVoiceSendTimeout(
    FileSystem.readAsStringAsync(stable, {
      encoding: FileSystem.EncodingType.Base64,
    }),
    "Leitura do áudio"
  );
}

function voiceUploadAuthHeaders(): Record<string, string> {
  const session = getSession();
  const token = session?.access_token?.trim();
  if (!token) {
    throw new Error("Sessão expirada. Saia e entre novamente.");
  }
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };
  if (session?.refresh_token) {
    headers["X-Refresh-Token"] = session.refresh_token;
  }
  return headers;
}

/** Campos extra no multipart — alguns Android não enviam Authorization no uploadAsync. */
function voiceUploadAuthFormFields(): Record<string, string> {
  const session = getSession();
  const access = session?.access_token?.trim() || "";
  const refresh = session?.refresh_token?.trim() || "";
  const fields: Record<string, string> = {};
  if (access) fields.access_token = access;
  if (refresh) fields.refresh_token = refresh;
  return fields;
}

/** Renova sessão antes de POST caro (upload nativo não passa pelo interceptor axios). */
async function ensureFreshSessionForPost(): Promise<void> {
  const session = getSession();
  if (!session?.refresh_token || !sessionNeedsRefresh(session)) return;
  try {
    const next = await refreshSessionToken(session.refresh_token, session);
    setSession(next);
    if (onSessionPersist) {
      await onSessionPersist(next);
    }
  } catch {
    /* segue com token actual — API pode aceitar refresh no form/header */
  }
}

/** Multipart nativo (FileSystem.uploadAsync) não passa pelos interceptors axios. */
async function buildVoiceUploadHeaders(): Promise<Record<string, string>> {
  const headers = voiceUploadAuthHeaders();
  headers["X-EGO-Platform"] = Platform.OS;
  const integrity = await Promise.race([
    getPlayIntegrityToken(),
    new Promise<null>((resolve) => setTimeout(() => resolve(null), 800)),
  ]);
  if (integrity) {
    headers["X-Play-Integrity"] = integrity;
  }
  return headers;
}

/** Android/iOS: upload nativo (axios FormData falha com frequência em produção). */
export async function sendChatVoiceFileNative(opts: {
  uri: string;
  audioMime?: string;
  speak?: boolean;
  history?: ChatHistoryPayload;
}): Promise<SendChatResult> {
  const uri = (opts.uri || "").trim();
  if (!uri) {
    throw new Error("Gravação vazia.");
  }
  const audio_mime = normalizeVoiceMime(opts.audioMime);
  const base = API_V1.endsWith("/") ? API_V1 : `${API_V1}/`;
  const url = `${base}chat/messages`;
  const uploadUri = await stabilizeVoiceUri(uri);
  const res = await withVoiceSendTimeout(
    FileSystem.uploadAsync(url, uploadUri, {
      httpMethod: "POST",
      uploadType: FileSystem.FileSystemUploadType.MULTIPART,
      fieldName: "audio",
      mimeType: audio_mime,
      headers: await buildVoiceUploadHeaders(),
      parameters: {
        message: "",
        audio_mime,
        speak: opts.speak !== false ? "true" : "false",
        history: JSON.stringify(opts.history ?? []),
        ...voiceUploadAuthFormFields(),
        ...Object.fromEntries(
          Object.entries(deviceTimezonePayload()).map(([k, v]) => [k, String(v)])
        ),
      },
    })
  );
  if (res.status < 200 || res.status >= 300) {
    let detail = `Erro ${res.status} ao enviar áudio.`;
    try {
      const parsed = JSON.parse(res.body) as { error?: string };
      if (parsed.error) detail = parsed.error;
    } catch {
      /* ignore */
    }
    throw new ApiClientError(detail, res.status);
  }
  try {
    const body = unwrap<SendChatResult>(JSON.parse(res.body));
    if (!body.reply) {
      throw new Error("A API não devolveu resposta do assistente.");
    }
    return body;
  } catch (e) {
    if (e instanceof ApiClientError) throw e;
    throw new Error("Resposta inválida do servidor ao processar voz.");
  }
}

/** Envio de voz nativo (Android/iOS) — multipart via axios (fallback). */
export async function sendChatVoiceFile(opts: {
  uri: string;
  audioMime?: string;
  speak?: boolean;
  history?: ChatHistoryPayload;
}): Promise<SendChatResult> {
  const uri = (opts.uri || "").trim();
  if (!uri) {
    throw new Error("Gravação vazia.");
  }
  const audio_mime = normalizeVoiceMime(opts.audioMime);
  const ext = audio_mime.includes("webm") ? "webm" : audio_mime.includes("wav") ? "wav" : "m4a";
  const form = new FormData();
  form.append(
    "audio",
    {
      uri,
      name: `voice.${ext}`,
      type: audio_mime,
    } as unknown as Blob
  );
  form.append("message", "");
  form.append("audio_mime", audio_mime);
  form.append("speak", opts.speak !== false ? "true" : "false");
  form.append("history", JSON.stringify(opts.history ?? []));
  const tz = deviceTimezonePayload();
  form.append("timezone", tz.timezone);
  form.append("tz_offset_min", String(tz.tz_offset_min));
  const authFields = voiceUploadAuthFormFields();
  if (authFields.access_token) form.append("access_token", authFields.access_token);
  if (authFields.refresh_token) form.append("refresh_token", authFields.refresh_token);

  const { data } = await api.post("chat/messages", form, {
    timeout: TIMEOUT_CHAT_MS,
  });
  const body = unwrap<SendChatResult>(data);
  if (!body.reply) {
    throw new Error("A API não devolveu resposta do assistente.");
  }
  return body;
}

async function sendChatVoiceBase64FromUri(opts: {
  uri: string;
  audioMime?: string;
  speak?: boolean;
  history?: ChatHistoryPayload;
}): Promise<SendChatResult> {
  const uri = (opts.uri || "").trim();
  if (!uri) {
    throw new Error("Gravação vazia.");
  }
  const audioBase64 = await readVoiceBase64FromUri(uri);
  return sendChatVoiceMessage({
    audioBase64,
    audioMime: opts.audioMime,
    speak: opts.speak,
    history: opts.history,
  });
}

/** Android: JSON/base64 primeiro (axios + refresh); multipart nativo como fallback. iOS: nativo primeiro. */
export async function sendChatVoiceFromUri(opts: {
  uri: string;
  audioMime?: string;
  speak?: boolean;
  history?: ChatHistoryPayload;
}): Promise<SendChatResult> {
  if (Platform.OS === "web") {
    return sendChatVoiceFile(opts);
  }

  await ensureFreshSessionForPost();

  if (Platform.OS === "android") {
    try {
      return await sendChatVoiceBase64FromUri(opts);
    } catch (jsonErr) {
      try {
        return await sendChatVoiceFileNative(opts);
      } catch {
        try {
          return await sendChatVoiceFile(opts);
        } catch {
          throw jsonErr;
        }
      }
    }
  }

  try {
    return await sendChatVoiceFileNative(opts);
  } catch (nativeErr) {
    try {
      return await sendChatVoiceFile(opts);
    } catch {
      try {
        return await sendChatVoiceBase64FromUri(opts);
      } catch {
        throw nativeErr;
      }
    }
  }
}

/** Envio de voz no browser (Safari) — ficheiro binário, sem base64 no JSON. */
export async function sendChatVoiceBlob(opts: {
  blob: Blob;
  speak?: boolean;
  history?: ChatHistoryPayload;
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
  form.append("history", JSON.stringify(opts.history ?? []));
  const tzBlob = deviceTimezonePayload();
  form.append("timezone", tzBlob.timezone);
  form.append("tz_offset_min", String(tzBlob.tz_offset_min));

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
  history?: ChatHistoryPayload;
}): Promise<SendChatResult> {
  await ensureFreshSessionForPost();
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
      ...deviceTimezonePayload(),
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

export async function fetchSharedCalendars(): Promise<SharedCalendar[]> {
  const { data } = await api.get("shared-calendars");
  const body = unwrap<{ shared_calendars: SharedCalendar[] }>(data);
  return body.shared_calendars ?? [];
}

export async function fetchSharedCalendar(calendarId: string): Promise<SharedCalendar> {
  const { data } = await api.get(`shared-calendars/${calendarId}`);
  const body = unwrap<{ calendar: SharedCalendar }>(data);
  if (!body.calendar) throw new Error("Agenda não encontrada.");
  return body.calendar;
}

export async function addSharedCalendarMember(
  calendarId: string,
  contact: string
): Promise<SharedCalendarMember> {
  const raw = contact.trim();
  const payload =
    raw.includes("@") ? { email: raw } : { phone: raw, contact: raw };
  const { data } = await api.post(`shared-calendars/${calendarId}/members`, payload);
  const body = unwrap<{ member: SharedCalendarMember }>(data);
  if (!body.member) throw new Error("Convite não devolvido pelo servidor.");
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
  event: { title: string; scheduled_at: string; announce?: string }
): Promise<WellnessJourney | null> {
  const { data } = await api.post(`shared-calendars/${calendarId}/events`, event);
  const body = unwrap<{ wellness_journey?: WellnessJourney }>(data);
  return body.wellness_journey ?? null;
}

export async function dismissSharedCalendarEvent(
  calendarId: string,
  eventId: string
): Promise<void> {
  await api.post(`shared-calendars/${calendarId}/events/${eventId}/dismiss`);
}

export async function respondEntreNosEvent(
  calendarId: string,
  eventId: string,
  accept: boolean
): Promise<{ event: SharedCalendarEvent; wellness_journey?: WellnessJourney }> {
  const { data } = await api.post(`shared-calendars/${calendarId}/events/${eventId}/respond`, {
    accept,
  });
  const body = unwrap<{ event: SharedCalendarEvent; wellness_journey?: WellnessJourney }>(data);
  if (!body.event) throw new Error("Resposta não devolvida pelo servidor.");
  return { event: body.event, wellness_journey: body.wellness_journey };
}

export async function deleteSharedCalendar(calendarId: string): Promise<void> {
  await api.delete(`shared-calendars/${calendarId}`);
}

export async function respondSharedCalendarMemberInvite(
  memberId: string,
  accept: boolean
): Promise<void> {
  await api.post(`shared-calendars/member-invites/${memberId}/respond`, { accept });
}

export function localDateTimeToIso(dateBr: string, timeHm: string): string | null {
  const dm = dateBr.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  const tm = timeHm.trim().match(/^(\d{1,2}):(\d{2})$/);
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

export async function logoutApi(): Promise<void> {
  try {
    await api.post("auth/logout");
  } catch {
    /* ignore */
  }
}

export { STORAGE_KEY };
