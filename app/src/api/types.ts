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
  intro_months?: number;
  price_after_brl?: number;
  campaign_ends_at?: string | null;
  checkout_url?: string | null;
  limits: PlanLimitsInfo;
};

/** Cupom parceiro / influenciadora (esconde Lançamento + 10% na 1ª compra). */
export type ReferralPlanOffer = {
  active: boolean;
  label?: string;
  partner_code?: string;
  partner_name?: string;
  discount_percent?: number;
  hide_launch_offer?: boolean;
  tagline?: string;
};

export type ReferralBenefitInfo = {
  active?: boolean;
  hide_launch_offer?: boolean;
  discount_percent?: number;
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
  /** E-mail listado em EGO_TEST_TOTAL_EMAILS no servidor (Railway). */
  is_test_total?: boolean;
  team_seats?: number | null;
  plan_type?: string;
  referral_benefit?: ReferralBenefitInfo | null;
  referral_offer?: ReferralPlanOffer | null;
};

export type AccessResponse = ApiOk<AccessInfo>;

export type Reminder = {
  id: string;
  title?: string;
  scheduled_at?: string;
  announce?: string;
  dismissed?: boolean;
  shopping_items?: ShoppingListItem[];
};

export type ShoppingListItem = {
  id: string;
  reminder_id?: string | null;
  title?: string;
  category?: string;
  done?: boolean;
};

export type AgendaDraftItem = {
  type: "reminder" | "shopping_orphan";
  title?: string;
  scheduled_at?: string;
  shopping_items?: { title: string; category?: string }[];
  category?: string;
  assign_to?: {
    relationship?: string;
    assignee_hint?: string;
    task?: string;
  };
  shared_calendar_id?: string;
  shared_calendar_name?: string;
};

export type AgendaDraft = {
  id: string;
  comfort_reply?: string;
  items?: AgendaDraftItem[];
  created_at?: string;
  status?: string;
};

export type NightDumpResult = {
  comfort_reply: string;
  items: AgendaDraftItem[];
  transcript?: string;
  draft?: AgendaDraft;
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
  invited_phone?: string;
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
  invite_status?: "none" | "pending" | "confirmed" | "declined";
  responded_by_user_id?: string;
  responded_at?: string;
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

export type PendingCalendarInvite = {
  member_id: string;
  calendar_id: string;
  calendar_name?: string;
  owner_name?: string;
  invited_email?: string;
  invited_phone?: string;
  invited_phone_display?: string;
  is_entre_nos?: boolean;
  role?: string;
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
  shared_events_saved?: (SharedCalendarEvent & { calendar_name?: string })[];
  shared_calendars_saved?: SharedCalendar[];
  shared_members_saved?: SharedCalendarMember[];
  /** openai_realtime = áudio já reproduzido no browser */
  voice_engine?: string;
  /** Contadores atualizados após esta mensagem (barra de uso no chat). */
  access?: AccessInfo;
  wellness_journey?: WellnessJourney;
};

export type AppUpdateInfo = {
  latest_version: string;
  play_store_url: string;
  ios_update_url?: string;
  message?: string;
  /** Version code Play — Android compara se versionName falhar. */
  android_version_code?: number;
};

export type PublicHealthInfo = {
  ok?: boolean;
  service?: string;
  maintenance?: boolean;
  maintenance_message?: string;
  app_update?: AppUpdateInfo;
};

export type HealthInfo = {
  ok?: boolean;
  service: string;
  supabase_configured: boolean;
  gemini_configured: boolean;
};

export type StreakSlice = {
  current: number;
  longest: number;
  last_date?: string;
  active_today?: boolean;
  at_risk?: boolean;
};

export type StreakInfo = StreakSlice & {
  /** Ofensiva do desabafo noturno (noites seguidas). */
  night_dump?: StreakSlice;
};

export type WellnessJourneyStep = {
  key: string;
  label: string;
  done: boolean;
  have?: number;
  need?: number;
};

export type CompanionEggColorItem = {
  id: string;
  label: string;
  emoji: string;
  price: number;
  owned: boolean;
  active: boolean;
  can_afford: boolean;
};

export type WeeklyChallenge = {
  week_key: string;
  days_done: number;
  days_goal: number;
  days_remaining: number;
  complete: boolean;
  today_done: boolean;
  bonus_stars?: number;
  bonus_awarded?: boolean;
  message: string;
};

export type WellnessJourney = {
  level: number;
  max_level: number;
  title: string;
  subtitle: string;
  emoji: string;
  today_task: string;
  why: string;
  progress: number;
  level_complete: boolean;
  mission_done_today?: boolean;
  missions_today?: number;
  missions_per_day?: number;
  steps: WellnessJourneyStep[];
  show_level_up: boolean;
  share_challenge: string;
  plan_nudge?: string | null;
  journey_finished: boolean;
  companion_stage?: string;
  companion_stage_label?: string;
  companion_sprite_emoji?: string;
  companion_name?: string;
  companion_name_setup_done?: boolean;
  care_percent?: number;
  stars?: number;
  companion_egg_color?: string;
  egg_color_shop?: CompanionEggColorItem[];
  weekly_challenge?: WeeklyChallenge;
};

export type PausaEgoWeekDot = {
  date: string;
  done: boolean;
  today: boolean;
};

export type DailyCareSeasonalEvent = {
  key: string;
  emoji: string;
  title: string;
  tagline: string;
  bonus_seeds: number;
  decor_emoji?: string;
  ends_at?: string;
  active?: boolean;
};

export type DailyCareQuizOption = {
  key: string;
  label: string;
  emoji: string;
};

export type DailyCareWeeklyQuiz = {
  week_key: string;
  quiz_id: string;
  question: string;
  options: DailyCareQuizOption[];
  reward_seeds: number;
  done: boolean;
  answer_key?: string | null;
};

export type DailyCareSocialInvite = {
  title: string;
  emoji: string;
  message: string;
  share_hook: string;
};

export type PausaExerciseStep = {
  text: string;
  seconds: number;
};

export type PausaDailyExercise = {
  key: string;
  emoji: string;
  title: string;
  subtitle: string;
  duration_seconds: number;
  mode: "breath" | "steps";
  focus?: string;
  mood_boosted?: boolean;
  lonely_boosted?: boolean;
  anywhere_friendly?: boolean;
  breath_inhale?: number;
  breath_exhale?: number;
  steps?: PausaExerciseStep[];
};

export type PausaPlanBenefit = {
  plan_tier: string;
  plan_label: string;
  headline: string;
  detail: string;
  techniques_unlocked: number;
  techniques_total: number;
  upgrade_tier?: string | null;
  upgrade_hint?: string;
};

export type PausaEgoInfo = {
  streak_current: number;
  streak_longest: number;
  today_done: boolean;
  total_sessions: number;
  moment_key: string;
  moment_emoji: string;
  moment_title: string;
  moment_prompt: string;
  share_line: string;
  week_dots: PausaEgoWeekDot[];
  last_kind?: string | null;
  daily_exercise?: PausaDailyExercise;
  plan_benefit?: PausaPlanBenefit;
  tomorrow_teaser?: { emoji: string; title: string };
  anywhere_line?: string;
  retention_line?: string;
  lonely_boosted?: boolean;
};

export type DailyCareMood = {
  key: string;
  emoji: string;
  label: string;
};

export type DailyCareQuestion = {
  index: number;
  total: number;
  text: string;
};

export type DailyCareCrisisBridge = {
  show: boolean;
  title: string;
  subtitle: string;
  exercise_key: string;
  duration_seconds: number;
  cvv_line: string;
  chat_draft?: string;
};

export type DailyCareGentleness = {
  gentle_mode: boolean;
  mirror_line?: string;
  calm_streak_current?: number;
  calm_streak_longest?: number;
  survival_streak_current?: number;
  survival_streak_longest?: number;
  survival_streak_line?: string;
  held_note?: string;
  crisis_bridge?: DailyCareCrisisBridge;
  night_garden?: boolean;
  sunday_garden?: boolean;
  lonely_note_today?: boolean;
  tagline?: string;
};

export type DailyCareInfo = {
  current: number;
  longest: number;
  last_date?: string;
  checked_today: boolean;
  at_risk: boolean;
  last_mood?: string;
  last_mood_emoji: string;
  last_mood_label: string;
  total_checkins: number;
  question: DailyCareQuestion;
  moods: DailyCareMood[];
  can_share: boolean;
  share_hook: string;
  ranking?: DailyCareRanking;
  garden_stage?: number;
  garden_label?: string;
  garden_emoji?: string;
  monster_line?: string;
  daily_mission?: string;
  daily_mission_action?: string;
  seeds?: number;
  decor_unlocked?: DailyCareDecor[];
  daily_goals?: DailyCareGoal[];
  adventure?: DailyCareAdventure;
  shop_items?: DailyCareShopItem[];
  shop_owned?: DailyCareShopOwned[];
  shop_week_label?: string;
  shop_rotation_reset?: string;
  shop_base_complete?: boolean;
  shop_rotating_available?: number;
  seed_history?: DailyCareSeedHistoryEntry[];
  mood_journal?: DailyCareMoodJournalEntry[];
  all_goals_done?: boolean;
  all_goals_bonus?: number;
  goals_bonus_granted?: boolean;
  avatar_congrats?: string;
  seasonal_event?: DailyCareSeasonalEvent | null;
  weekly_quiz?: DailyCareWeeklyQuiz | null;
  social_invite?: DailyCareSocialInvite | null;
  gentleness?: DailyCareGentleness | null;
};

export type DailyCareShopItem = {
  id: string;
  emoji: string;
  label: string;
  price: number;
  owned: boolean;
  can_afford: boolean;
  rotating?: boolean;
};

export type DailyCareShopOwned = {
  id: string;
  emoji: string;
  label: string;
};

export type DailyCareSeedHistoryEntry = {
  action: string;
  amount: number;
  label: string;
  date: string;
};

export type DailyCareMoodJournalEntry = {
  date: string;
  mood: string;
  emoji: string;
  label: string;
  note?: string;
};

export type DailyCareDecor = {
  id: string;
  emoji: string;
  label: string;
  min_days: number;
};

export type DailyCareGoal = {
  key: string;
  label: string;
  emoji: string;
  done: boolean;
  seeds_reward: number;
  locked?: boolean;
  kind?: "checkin" | "tap" | "breathe" | "adventure";
  surprise?: boolean;
  gentle?: boolean;
};

export type DailyCareAdventure = {
  active: boolean;
  progress: number;
  title: string;
  subtitle: string;
  can_collect: boolean;
  collected: boolean;
  reward_seeds: number;
};

export type DailyCareRankingLadder = {
  min_days: number;
  emoji: string;
  label: string;
  reached: boolean;
};

export type DailyCareRanking = {
  tier_index: number;
  tier_total: number;
  tier_emoji: string;
  tier_label: string;
  next_tier_days?: number | null;
  next_tier_label?: string | null;
  personal_best: number;
  community_top_days: number;
  days_to_next_tier: number;
  challenge_line: string;
  ladder: DailyCareRankingLadder[];
  milestones?: DailyCareRankingLadder[];
};

export type DelegationRequest = {
  id: string;
  from_user_id?: string;
  to_user_id?: string;
  title?: string;
  scheduled_at?: string;
  task_description?: string;
  assignee_label?: string;
  assistant_name?: string;
  requester_name?: string;
  status?: string;
  created_at?: string;
};

export type DashboardData = {
  health: HealthInfo | null;
  me: MeData | null;
  access: AccessInfo | null;
  reminders: Reminder[];
  agenda: AgendaItem[];
  agenda_drafts?: AgendaDraft[];
  shopping_orphans?: ShoppingListItem[];
  delegation_requests?: DelegationRequest[];
  streak?: StreakInfo;
  wellness_journey?: WellnessJourney;
  pausa_ego?: PausaEgoInfo;
  daily_care?: DailyCareInfo;
  shared_calendars?: SharedCalendar[];
  pending_calendar_invites?: PendingCalendarInvite[];
  messages: ChatMessage[];
  chat_local_history?: boolean;
};
