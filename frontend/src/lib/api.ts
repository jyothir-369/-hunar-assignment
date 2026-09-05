// API client for the Hunar FastAPI backend.

import axios, { AxiosError } from "axios";

import type {
  AgentListResponse,
  ApolloSearchResponse,
  Campaign,
  Candidate,
  CandidateListResponse,
  CampaignListResponse,
  HunarAgent,
} from "@/types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

if (!API_URL) {
  // Fail loudly at startup instead of silently calling a wrong host.
  // NEXT_PUBLIC_API_URL is baked in at build time — if it's missing on
  // Vercel, every request will hit a stale/wrong origin.
  // eslint-disable-next-line no-console
  console.error(
    "[api] NEXT_PUBLIC_API_URL is not set — backend calls will fail.",
  );
}

export const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Normalize the error so consumers can always read .message
    // No `error.response` → request never reached the server (DNS, CORS
    // preflight blocked, wrong host, server down, offline, etc.).
    if (!error.response) {
      return Promise.reject(
        new Error(
          `Cannot reach backend at ${API_URL} — check NEXT_PUBLIC_API_URL. (${error.message})`,
        ),
      );
    }
    const message =
      (error.response?.data as { detail?: string | unknown[] } | undefined)
        ?.detail?.toString() ?? error.message ?? "Request failed";
    return Promise.reject(new Error(message));
  },
);

export interface ListParams {
  page?: number;
  page_size?: number;
  language?: string;
  status?: string;
  campaign_id?: string;
  agent_status?: string;
  candidate_status?: string;
}

// ─── AGENTS ──────────────────────────────────────────────

export const agentsApi = {
  list: (params?: ListParams) =>
    api.get<AgentListResponse>("/api/agents/", { params }).then((r) => r.data),
  get: (id: string) =>
    api.get<HunarAgent>(`/api/agents/${id}`).then((r) => r.data),
  create: (data: Partial<HunarAgent>) =>
    api.post<HunarAgent>("/api/agents/", data).then((r) => r.data),
  update: (id: string, data: Partial<HunarAgent>) =>
    api.put<HunarAgent>(`/api/agents/${id}`, data).then((r) => r.data),
  delete: (id: string) =>
    api.delete(`/api/agents/${id}`).then((r) => r.data),
};

// ─── CAMPAIGNS ───────────────────────────────────────────

export interface CampaignLaunchPayload {
  retry_config?: { max_retry_count?: number; retry_interval_hours?: number };
  guardrails?: {
    allowed_days?: string[];
    earliest_call_time?: string;
    last_call_time?: string;
  };
  timezone?: string;
}

export const campaignsApi = {
  list: (params?: ListParams) =>
    api
      .get<CampaignListResponse>("/api/campaigns/", { params })
      .then((r) => r.data),
  get: (id: string) =>
    api.get<Campaign>(`/api/campaigns/${id}`).then((r) => r.data),
  create: (data: Partial<Campaign>) =>
    api.post<Campaign>("/api/campaigns/", data).then((r) => r.data),
  update: (id: string, data: Partial<Campaign>) =>
    api.put<Campaign>(`/api/campaigns/${id}`, data).then((r) => r.data),
  launch: (id: string, payload: CampaignLaunchPayload) =>
    api
      .post<Campaign>(`/api/campaigns/${id}/launch`, payload)
      .then((r) => r.data),
};

// ─── CANDIDATES ──────────────────────────────────────────

export const candidatesApi = {
  list: (params?: ListParams) =>
    api
      .get<CandidateListResponse>("/api/candidates/", { params })
      .then((r) => r.data),
  get: (id: string) =>
    api.get<Candidate>(`/api/candidates/${id}`).then((r) => r.data),
  create: (data: Partial<Candidate>) =>
    api.post<Candidate>("/api/candidates/", data).then((r) => r.data),
  bulkCreate: (data: {
    campaign_id: string;
    candidates: Partial<Candidate>[];
  }) =>
    api
      .post<{ created: number; candidate_ids: string[] }>(
        "/api/candidates/bulk",
        data,
      )
      .then((r) => r.data),
  delete: (id: string) =>
    api.delete(`/api/candidates/${id}`).then((r) => r.data),
};

// ─── PEOPLE SEARCH (Apollo.io) ───────────────────────────

export interface PeopleSearchPayload {
  job_title: string;
  seniority_levels: string[];
  locations: string[];
  page?: number;
  per_page?: number;
}

export const peopleApi = {
  search: (payload: PeopleSearchPayload) =>
    api
      .post<ApolloSearchResponse>("/api/people/search", payload)
      .then((r) => r.data),
};

// ─── SETTINGS ───────────────────────────────────────────

export interface RuntimeSettings {
  app: {
    name: string;
    version: string;
    debug: boolean;
    frontend_url: string;
    webhook_url: string | null;
  };
  database: {
    target: string;
    ok: boolean;
    error: string | null;
  };
  demo?: {
    seeded: boolean;
  };
  integrations: {
    hunar: { configured: boolean; key_preview: string; base_url: string };
    apollo: { configured: boolean; key_preview: string; fallback: string };
    webhook_secret: {
      configured: boolean;
      key_preview: string;
      validation: string;
    };
  };
  host: { hostname: string | null; pid: number };
}

export const settingsApi = {
  get: () => api.get<RuntimeSettings>("/api/settings/").then((r) => r.data),
};

// ─── ADMIN (demo data) ──────────────────────────────────

export interface SeedDemoResponse {
  ok: boolean;
  stdout: string;
  stderr: string;
}

export const adminApi = {
  // Caller supplies the ADMIN_TOKEN (read from process.env.NEXT_PUBLIC_ADMIN_TOKEN
  // or pasted into a Settings input). The backend rejects this with 503 if
  // the env var is unset, so a missing token never falls back to "open".
  seedDemo: (token: string) =>
    api
      .post<SeedDemoResponse>(
        "/api/admin/seed-demo",
        {},
        { headers: { "X-Admin-Token": token } },
      )
      .then((r) => r.data),
};

// ─── CALLS (Hunar proxy) ─────────────────────────────────

export interface HunarCallResult {
  source: "local" | "hunar";
  candidate_id: string | null;
  result: Record<string, unknown>;
  interest_level?: string | null;
  qualification_status?: string | null;
}

export interface HunarCallEnvelope {
  call: Record<string, unknown>;
  candidate_id: string | null;
  local_status?: string;
}

export const callsApi = {
  get: (callId: string) =>
    api
      .get<HunarCallEnvelope>(`/api/calls/${callId}`)
      .then((r) => r.data),
  getResult: (callId: string) =>
    api
      .get<HunarCallResult>(`/api/calls/${callId}/result`)
      .then((r) => r.data),
};

export { API_URL };
