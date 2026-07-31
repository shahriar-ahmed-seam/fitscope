// Mirrors backend/app/schemas.py

export type Coverage = "covered" | "partial" | "missing";
export type Category = "must_have" | "nice_to_have" | "responsibility";
export type CheckStatus = "pass" | "warn" | "fail";

export interface Requirement {
  id: string;
  text: string;
  category: Category;
  keywords: string[];
}

export interface JobSpec {
  role_title: string | null;
  company: string | null;
  seniority: string | null;
  years_required: number | null;
  location: string | null;
  requirements: Requirement[];
  hard_skills: string[];
  soft_skills: string[];
  extraction_mode: "llm" | "heuristic";
}

export interface Evidence {
  requirement: Requirement;
  coverage: Coverage;
  score: number;
  decided_by: "judge" | "reranker" | "lexical";
  confidence: number | null;
  justification: string | null;
  best_bullet_id: string | null;
  best_bullet_text: string | null;
  best_bullet_section: string | null;
  supporting_bullet_ids: string[];
  keyword_hits: string[];
  keyword_misses: string[];
}

export interface AtsCheck {
  id: string;
  label: string;
  status: CheckStatus;
  points: number;
  max_points: number;
  detail: string;
  fix: string | null;
}

export interface AtsResult {
  score: number;
  checks: AtsCheck[];
  keyword_coverage: number;
  matched_keywords: string[];
  missing_keywords: string[];
}

export interface BulletRewrite {
  bullet_id: string | null;
  original: string;
  rewritten: string;
  reason: string;
  targets: string[];
}

export interface Suggestions {
  tailored_summary: string | null;
  rewrites: BulletRewrite[];
  add_these: string[];
  quick_wins: string[];
  mode: "llm" | "heuristic";
}

export interface ScoreBreakdown {
  overall: number;
  semantic_fit: number;
  ats_readiness: number;
  must_have_coverage: number;
  nice_to_have_coverage: number;
  responsibility_coverage: number;
  covered: number;
  partial: number;
  missing: number;
  verdict: string;
  verdict_detail: string;
}

export interface ResumeStats {
  word_count?: number;
  char_count?: number;
  bullet_count?: number;
  bullets_with_metrics?: number;
  sections?: string[];
  skills_detected?: string[];
  years_experience?: number | null;
  source_kind?: string;
  pages?: number | null;
  parse_warnings?: string[];
  emails?: number;
  links?: number;
}

export interface PipelineInfo {
  candidate_lines?: number;
  requirement_count?: number;
  retrieval?: string;
  decider?: string;
  jd_extraction?: string;
  suggestions?: string;
  weights?: Record<string, number>;
  thresholds?: Record<string, number>;
}

export interface AnalysisReport {
  public_id: string | null;
  share_url: string | null;
  created_at: string | null;
  duration_ms: number;
  job: JobSpec;
  scores: ScoreBreakdown;
  evidence: Evidence[];
  ats: AtsResult;
  suggestions: Suggestions;
  resume_stats: ResumeStats;
  pipeline: PipelineInfo;
}

export interface ReportSummary {
  public_id: string;
  role_title: string | null;
  company: string | null;
  overall_score: number | null;
  semantic_score: number | null;
  ats_score: number | null;
  verdict: string | null;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  capabilities: Record<string, boolean>;
  models: Record<string, string | null>;
}

export interface QuotaResponse {
  limit: number;
  remaining: number | null;
  unlimited: boolean;
}
