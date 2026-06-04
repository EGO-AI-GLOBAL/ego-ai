export type ApiOk<T> = { ok: true } & T;
export type ApiErr = { ok: false; error: string };

export type SessionUser = {
  id: string;
  email: string;
};

export type AuthSession = {
  access_token: string;
  refresh_token: string;
  expires_at?: number | null;
  user: SessionUser;
};

export type HealthResponse = ApiOk<{
  service: string;
  supabase_configured: boolean;
  gemini_configured: boolean;
}>;

export type PlanTier =
  | "essential"
  | "connection"
  | "premium"
  | "total"
  | "enterprise";

export type StripeCheckoutLinks = {
  monthly_url: string | null;
  annual_url: string | null;
  connection_url?: string | null;
  /** Oferta de lançamento BR (R$ 9,90) — limites Conexão */
  launch_url?: string | null;
  premium_url?: string | null;
  total_url?: string | null;
  enterprise_url?: string | null;
  int_connection_url?: string | null;
  int_premium_url?: string | null;
  int_premium_annual_url?: string | null;
  int_total_url?: string | null;
  int_total_annual_url?: string | null;
  int_enterprise_url?: string | null;
  essential?: null;
  /** Planos equipe: team.br.connection['10'] */
  team?: {
    br?: Partial<Record<"connection" | "premium" | "total", Record<string, string | null>>>;
    int?: Partial<Record<"connection" | "premium" | "total", Record<string, string | null>>>;
  };
};

export type PlanLimitsInfo = {
  monthly_tokens: number;
  daily_text_messages: number;
  daily_voice_messages: number;
  daily_tts_replies: number;
  max_agenda_items: number;
  max_reminders: number;
  audio_speed_multipliers: number[];
};

export type PlanCatalogItem = {
  tier: PlanTier;
  label: string;
  price_brl: number;
  limits: PlanLimitsInfo;
};

/** Promo lançamento (API /plans → launch_offer). */
export type LaunchPlanOffer = {
  tier: PlanTier;
  label: string;
  price_brl: number;
  price_label?: string;
  tagline?: string;
  checkout_url?: string | null;
  limits: PlanLimitsInfo;
};

export type MeData = {
  user_id: string;
  email: string | null;
  profile: Record<string, unknown> | null;
  persona_configured?: boolean;
  persona: { avatar_id: string; voice_id: string } | null;
  access: { allowed: boolean; status: string };
  stripe_checkout: StripeCheckoutLinks;
};

export type MeResponse = ApiOk<MeData>;

export type AccessInfo = {
  access_allowed: boolean;
  access_status: string;
  plan_tier?: PlanTier;
  plan_label?: string;
  plan_price_brl?: number;
  daily_messages_ok: boolean;
  daily_messages_used: number;
  daily_messages_limit: number;
  daily_text_messages_ok?: boolean;
  daily_text_messages_used?: number;
  daily_text_messages_limit?: number;
  daily_voice_messages_ok?: boolean;
  daily_voice_messages_used?: number;
  daily_voice_messages_limit?: number;
  daily_tts_ok?: boolean;
  daily_tts_used?: number;
  daily_tts_limit?: number;
  monthly_tokens_ok: boolean;
  monthly_tokens_message: string;
  monthly_tokens_used: number;
  monthly_tokens_limit: number;
  agenda_ok?: boolean;
  agenda_used?: number;
  agenda_limit?: number;
  reminders_ok?: boolean;
  reminders_used?: number;
  reminders_limit?: number;
  audio_speed_allowed?: number[];
  /** Histórico de chat só no dispositivo (servidor não guarda mensagens). */
  chat_local_history?: boolean;
  is_pro: boolean;
  team_seats?: number | null;
  plan_type?: string;
};

export type AccessResponse = ApiOk<AccessInfo>;

export type Reminder = {
  id: string;
  title?: string;
  scheduled_at?: string;
  announce?: string;
  dismissed?: boolean;
};

export type AgendaItem = {
  id: string;
  titulo?: string;
  horario?: string;
  dias_da_semana?: string;
};

export type SharedCalendarMember = {
  id: string;
  calendar_id?: string;
  user_id?: string | null;
  invited_email?: string;
  display_name?: string;
  role?: "owner" | "member";
  status?: string;
  created_at?: string;
};

export type SharedCalendarEvent = {
  id: string;
  calendar_id?: string;
  created_by_user_id?: string;
  title?: string;
  scheduled_at?: string;
  announce?: string;
  dismissed?: boolean;
};

export type SharedCalendar = {
  id: string;
  owner_user_id?: string;
  name?: string;
  created_at?: string;
  is_owner?: boolean;
  member_count?: number;
  members?: SharedCalendarMember[];
  events?: SharedCalendarEvent[];
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  msg_id?: string | null;
  created_at?: string;
};

/** Contexto enviado à API (últimos turnos guardados no aparelho). */
export type ChatHistoryPayload = {
  role: "user" | "assistant";
  content: string;
}[];

export type SendChatResult = {
  reply: string;
  /** Texto transcrito no browser (voz rápida); ausente se enviou áudio ao servidor. */
  user_transcript?: string;
  warnings?: string[];
  user_message_id?: string | null;
  assistant_message_id?: string | null;
  tts_audio_base64?: string;
  tts_mime?: string;
  tts_voice_id?: string;
  tts_error?: string;
  language?: string;
  agenda_saved?: AgendaItem[];
  reminders_saved?: Reminder[];
  /** openai_realtime = áudio já reproduzido no browser */
  voice_engine?: string;
};

export type HealthInfo = {
  ok?: boolean;
  service: string;
  supabase_configured: boolean;
  gemini_configured: boolean;
};

export type DashboardData = {
  health: HealthInfo | null;
  me: MeData | null;
  access: AccessInfo | null;
  reminders: Reminder[];
  agenda: AgendaItem[];
  shared_calendars?: SharedCalendar[];
  messages: ChatMessage[];
  chat_local_history?: boolean;
};
