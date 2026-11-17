export const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api").replace(/\/$/, "");

export type CandidateProfile = {
  id: number;
  filename: string;
  name: string;
  years_experience: number;
  skills: string[];
  education: string[];
  preferred_roles: string[];
};

export type MatchScore = {
  total_score: number;
  semantic_score: number;
  skill_score: number;
  experience_score: number;
  tfidf_similarity: number;
  skill_jaccard: number;
  matched_skills: string[];
  missing_skills: string[];
};

export type Job = {
  id: number;
  title: string;
  company: string;
  location: string;
  country: string;
  region?: string | null;
  engineering_branch?: string | null;
  domain?: string | null;
  is_live?: boolean;
  work_mode: "remote" | "hybrid" | "onsite";
  salary_min_usd: number;
  salary_max_usd: number;
  salary_display?: string | null;
  salary_is_estimated: boolean;
  experience_level: "entry" | "mid" | "senior" | "lead";
  description: string;
  skills: string[];
  category: string;
  apply_url: string;
  source: string;
  posted_at: string;
  match?: MatchScore;
};

export type JobPage = {
  items: Job[];
  total: number;
  page: number;
  limit: number;
};

export type MarketOverview = {
  jobs_analyzed: number;
  median_salary_usd: number | null;
  remote_role_share: number;
  top_skills: { skill: string; frequency: number; mean_salary_usd: number | null }[];
  salary_distribution: {
    experience_level: string;
    work_mode: string;
    count: number;
    minimum: number;
    p25: number;
    median: number;
    p75: number;
    maximum: number;
  }[];
  job_volume: { category: string; work_mode: string; job_count: number }[];
  engineering_regional_demand: { engineering_branch: string; region: string; job_count: number }[];
  personal_skill_gap_roi: { skill: string; high_scoring_jobs: number; mean_match_score: number }[];
};

export type Taxonomy = {
  branches: Record<string, string[]>;
  regions: string[];
};

export type LiveSearchFilters = {
  q?: string;
  region?: string;
  engineering_branch?: string;
  domain?: string;
};

export type EtlRun = {
  id: number;
  source: string;
  jobs_fetched: number;
  duplicates_skipped: number;
  invalid_dropped: number;
  run_at: string;
};

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }), ...init?.headers },
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}
