// Hunar API types — shared across the app.

export interface HunarAgent {
  id: string;
  name: string;
  hunar_agent_id: string;
  voice_persona: string;
  persona_name?: string | null;
  language: string;
  agent_prompt: string;
  introduction: string;
  objective?: string | null;
  result_prompt?: string | null;
  result_schema: Record<string, unknown>;
  status: string;
  summary?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentListResponse {
  count: number;
  results: HunarAgent[];
}

export interface Campaign {
  id: string;
  name: string;
  agent_id: string;
  job_title?: string | null;
  job_description?: string | null;
  guardrails: Record<string, unknown>;
  retry_config: Record<string, unknown>;
  timezone: string;
  status: string;
  total_candidates: number;
  stats?: CampaignStats | null;
  created_at: string;
  updated_at: string;
}

export interface CampaignStats {
  total: number;
  pending: number;
  initiated: number;
  in_progress: number;
  completed: number;
  not_connected: number;
  failed: number;
}

export interface CampaignListResponse {
  count: number;
  results: Campaign[];
}

export interface Candidate {
  id: string;
  campaign_id: string;
  hunar_call_id?: string | null;
  callee_name: string;
  mobile_number: string;
  email?: string | null;
  custom_data: Record<string, unknown>;
  status: string;
  interest_level?: string | null;
  qualification_status?: string | null;
  recording_url?: string | null;
  call_result?: Record<string, unknown> | null;
  request_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CandidateListResponse {
  count: number;
  results: Candidate[];
}

export interface CallEvent {
  id: string;
  hunar_call_id: string;
  candidate_id?: string | null;
  event_type: string;
  payload: Record<string, unknown>;
  received_at: string;
}

export interface ApolloCandidate {
  name: string;
  title: string;
  company: string;
  phone: string;
  email: string;
  linkedin_url: string;
  city: string;
  country: string;
  seniority: string;
  apollo_id: string;
}

export interface ApolloSearchResponse {
  source: "apollo" | "mock";
  count: number;
  candidates: ApolloCandidate[];
}

export const VOICE_PERSONAS = [
  "NEHA",
  "ROY",
  "ZOE",
  "SAM",
  "MIRA",
  "EESHA",
] as const;
export type VoicePersona = (typeof VOICE_PERSONAS)[number];

export const LANGUAGES = [
  "ENGLISH",
  "HINDI",
  "TAMIL",
  "TELUGU",
  "KANNADA",
  "MARATHI",
  "MALAYALAM",
  "GUJARATI",
  "BENGALI",
  "TURKISH",
  "ARABIC",
  "SPANISH",
] as const;
export type Language = (typeof LANGUAGES)[number];

export const CALL_STATUSES = [
  "PENDING",
  "INITIATED",
  "IN_PROGRESS",
  "COMPLETED",
  "NOT_CONNECTED",
  "FAILED",
  "CANCELLED",
] as const;
export type CallStatus = (typeof CALL_STATUSES)[number];

export const CAMPAIGN_STATUSES = [
  "DRAFT",
  "LAUNCHED",
  "RUNNING",
  "COMPLETED",
  "PAUSED",
  "CANCELLED",
] as const;
export type CampaignStatus = (typeof CAMPAIGN_STATUSES)[number];

export const CALL_STATUS_COLORS: Record<CallStatus, string> = {
  PENDING: "bg-slate-100 text-slate-700 border-slate-200",
  INITIATED: "bg-blue-100 text-blue-800 border-blue-200",
  IN_PROGRESS: "bg-amber-100 text-amber-800 border-amber-200",
  COMPLETED: "bg-emerald-100 text-emerald-800 border-emerald-200",
  NOT_CONNECTED: "bg-orange-100 text-orange-800 border-orange-200",
  FAILED: "bg-red-100 text-red-800 border-red-200",
  CANCELLED: "bg-slate-100 text-slate-500 border-slate-200",
};

export const CAMPAIGN_STATUS_COLORS: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700 border-slate-200",
  LAUNCHED: "bg-blue-100 text-blue-800 border-blue-200",
  RUNNING: "bg-amber-100 text-amber-800 border-amber-200",
  COMPLETED: "bg-emerald-100 text-emerald-800 border-emerald-200",
  PAUSED: "bg-orange-100 text-orange-800 border-orange-200",
  CANCELLED: "bg-slate-100 text-slate-500 border-slate-200",
};
