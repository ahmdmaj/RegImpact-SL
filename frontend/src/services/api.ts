/**
 * RegImpact-SL API Service
 * 
 * Typed API client mirroring FastAPI backend schemas for:
 * - Health check (GET /health)
 * - Regulatory clause versions (GET /regulations)
 * - Regulatory change impact analysis (POST /analysis)
 */

export type OutcomeStatus =
  | "APPLICABLE"
  | "NOT_APPLICABLE"
  | "CONDITIONAL_MISSING_DATA"
  | "CONDITIONAL_RULE"
  | "UNSUPPORTED";

export interface ProductItem {
  category: string;
  prepackaged?: boolean | null;
  product_name?: string | null;
}

export interface ProductionCapacity {
  value?: number | null;
  unit?: string | null;
  per_period?: string | null;
}

export interface Premises {
  type?: string | null;
  location_authority_area?: string | null;
  province?: string | null;
}

export interface Market {
  domestic?: boolean | null;
  export_flag?: boolean | null;
  import_flag?: boolean | null;
  b2b_only?: boolean | null;
}

export interface BusinessProfile {
  business_id?: string;
  industry?: string | null;
  activity?: string | null;
  employee_count?: number | null;
  products?: ProductItem[];
  production_capacity?: ProductionCapacity | null;
  premises?: Premises | null;
  market?: Market | null;
  existing_licences?: string[];
  as_at_date?: string | null;
  packaged_in_presence_of_purchaser?: boolean | null;
}

export interface PatchOperation {
  patch_type: "substitute" | "insert" | "omit" | "repeal";
  target_text: string;
  replacement_text?: string;
  enacted_date?: string | null;
  effective_date?: string | null;
  source_gazette?: string | null;
}

export interface ClauseVersion {
  clause_id: string;
  instrument: string;
  version_number: number;
  text: string;
  valid_from: string;
  valid_to?: string | null;
  applied_patches?: PatchOperation[];
}

export interface EvaluationTraceEntry {
  field: string;
  target_value: unknown;
  observed_value: unknown;
  result: "TRUE" | "FALSE" | "UNKNOWN";
  op?: string;
}

export interface BusinessImpact {
  obligation_type: string;
  affected_activities: string[];
  affected_documents: string[];
  action_items: string[];
  timeline_note?: string | null;
}

export interface RuleAnalysisDetail {
  rule_id: string;
  clause: string;
  instrument: string;
  authority: string;
  status: OutcomeStatus;
  reason?: string | null;
  temporal_status?: string | null;
  quote_span?: string | null;
  missing_fields: string[];
  counterfactuals: string[];
  evaluation_trace: EvaluationTraceEntry[];
  impact?: BusinessImpact | null;

  // Milestone 7 Persistent Provenance & Audit Trail
  document_title?: string | null;
  document_id?: string | null;
  page_number?: number | null;
  char_start?: number | null;
  char_end?: number | null;
  review_status?: string | null;
  coverage_gap?: boolean;
}

export interface StructuredImpactReport {
  as_at_date: string;
  total_rules_evaluated: intOrNumber;
  applicable_rules_count: intOrNumber;
  conditional_rules_count: intOrNumber;
  not_applicable_rules_count: intOrNumber;
  unsupported_rules_count: intOrNumber;
  conditional_missing_data_count?: intOrNumber;
  conditional_rule_count?: intOrNumber;
  missing_fields: string[];
  clarifying_questions: string[];
  action_checklist: string[];
  affected_activities: string[];
  affected_documents: string[];
  narrative_summary?: string | null;
  evaluations: RuleAnalysisDetail[];
}

type intOrNumber = number;

export interface AnalysisRequest {
  business_profile: BusinessProfile;
  as_at_date?: string;
  clause_ids?: string[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type UserRole = "admin" | "reviewer" | "sme_user";

let currentUserRole: UserRole = "admin";

/**
 * Get current active user role from memory or localStorage
 */
export function getCurrentUserRole(): UserRole {
  if (typeof window !== "undefined") {
    const saved = localStorage.getItem("regimpact_user_role");
    if (saved === "admin" || saved === "reviewer" || saved === "sme_user") {
      currentUserRole = saved;
    }
  }
  return currentUserRole;
}

/**
 * Update current active user role and persist to localStorage
 */
export function setCurrentUserRole(role: UserRole): void {
  currentUserRole = role;
  if (typeof window !== "undefined") {
    localStorage.setItem("regimpact_user_role", role);
    // Dispatch custom event so UI components can re-render reactively
    window.dispatchEvent(new CustomEvent("regimpact:role_change", { detail: { role } }));
  }
}

/**
 * Helper to attach X-User-Role and Content-Type headers
 */
export function getAuthHeaders(extraHeaders: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = {
    "X-User-Role": getCurrentUserRole(),
    ...extraHeaders,
  };
  return headers;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Health check endpoint
 */
export async function getHealth(): Promise<{ status: string }> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`, {
      method: "GET",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      cache: "no-store",
    });
    if (!res.ok) {
      throw new ApiError(res.status, `Health check failed: ${res.statusText}`);
    }
    return await res.json();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new Error(`Cannot connect to RegImpact backend at ${API_BASE_URL}. Ensure FastAPI is running.`);
  }
}

/**
 * Fetch statutory clause versions catalog
 */
export async function getRegulations(): Promise<ClauseVersion[]> {
  const res = await fetch(`${API_BASE_URL}/regulations`, {
    method: "GET",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new ApiError(res.status, `Failed to load regulations: ${res.statusText}`);
  }
  return await res.json();
}

/**
 * Run deterministic regulatory impact analysis
 */
export async function runAnalysis(request: AnalysisRequest): Promise<StructuredImpactReport> {
  const res = await fetch(`${API_BASE_URL}/analysis`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const errorJson = await res.json();
      if (errorJson.detail) {
        errorDetail = typeof errorJson.detail === "string" 
          ? errorJson.detail 
          : JSON.stringify(errorJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new ApiError(res.status, errorDetail);
  }
  return await res.json();
}

/**
 * Benchmark Evaluation Results Schemas (Milestone 7)
 */
export interface MetricCI {
  point_estimate: number;
  ci_lower: number;
  ci_upper: number;
  std_err: number;
  ci_level: number;
  n_bootstraps: number;
}

export interface ClassPerformance {
  precision: number;
  recall: number;
  f1: number;
  support: number;
}

export interface SystemMetrics {
  total_scenarios: number;
  accuracy: number;
  macro_f1: number;
  per_class: Record<string, ClassPerformance>;
  abstention_precision: number;
  abstention_recall: number;
  abstention_f1: number;
  missing_fields_accuracy: number;
  missing_fields_jaccard: number;
  c_sens: number;
  c_inv: number;
  c_comb: number;
  sens_pair_count: number;
  inv_pair_count: number;
  temporal_accuracy: number;
  coverage_gap_accuracy: number;
  direct_accuracy: number;
}

export interface PairedComparison {
  system_a: string;
  system_b: string;
  metric_a: number;
  metric_b: number;
  difference: number;
  ci_lower: number;
  ci_upper: number;
  p_value: number;
  statistically_significant: boolean;
  alpha: number;
  n_bootstraps: number;
  direction: string;
}

export interface EvaluationResultsPayload {
  timestamp: string;
  total_scenarios: number;
  n_bootstraps: number;
  metrics: Record<string, SystemMetrics>;
  confidence_intervals: Record<string, { accuracy: MetricCI }>;
  paired_comparisons_vs_system_p: Record<string, PairedComparison>;
}

/**
 * Fetch latest compiled benchmark evaluation results
 */
export async function getEvaluationResults(): Promise<EvaluationResultsPayload> {
  const res = await fetch(`${API_BASE_URL}/evaluation/results`, {
    method: "GET",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new ApiError(res.status, `Failed to load evaluation results: ${res.statusText}`);
  }
  return await res.json();
}

/**
 * Review Queue Schemas and Endpoints (Phase 2 & 3)
 */
export interface ReviewItem {
  rule_id: string;
  clause_id: string;
  clause_number?: string | null;
  document_id?: string | null;
  outcome_type: string;
  applies_if: Record<string, unknown>;
  exceptions: Array<Record<string, unknown>>;
  obligation: Record<string, unknown>;
  validity: Record<string, unknown>;
  source: Record<string, unknown>;
  review_status: string;
  clause_text?: string | null;
  quote_span?: string | null;
}

export interface ReviewDecisionPayload {
  reviewer_id?: string;
  rationale?: string;
  amendments?: Record<string, unknown>;
}

export interface DocumentUploadResponse {
  status: string;
  doc_id: string;
  title: string;
  authority: string;
  file_path: string;
  pages_indexed: number;
  rules_compiled: number;
}

/**
 * Fetch pending rules queue for human legal review
 */
export async function getPendingReviews(): Promise<ReviewItem[]> {
  const res = await fetch(`${API_BASE_URL}/admin/reviews`, {
    method: "GET",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new ApiError(res.status, `Failed to fetch pending reviews: ${res.statusText}`);
  }
  return await res.json();
}

/**
 * Approve a candidate rule
 */
export async function approveReview(
  ruleId: string,
  payload: ReviewDecisionPayload = {}
): Promise<{ status: string; rule_id: string; review_status: string; decision: string }> {
  const res = await fetch(`${API_BASE_URL}/admin/reviews/${encodeURIComponent(ruleId)}/approve`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const err = await res.json();
      if (err.detail) errorDetail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
    } catch {}
    throw new ApiError(res.status, errorDetail);
  }
  return await res.json();
}

/**
 * Reject a candidate rule
 */
export async function rejectReview(
  ruleId: string,
  payload: ReviewDecisionPayload = {}
): Promise<{ status: string; rule_id: string; review_status: string; decision: string }> {
  const res = await fetch(`${API_BASE_URL}/admin/reviews/${encodeURIComponent(ruleId)}/reject`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const err = await res.json();
      if (err.detail) errorDetail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
    } catch {}
    throw new ApiError(res.status, errorDetail);
  }
  return await res.json();
}

/**
 * Upload official PDF document to trigger ingestion and rule compilation
 */
export async function uploadDocument(formData: FormData): Promise<DocumentUploadResponse> {
  const res = await fetch(`${API_BASE_URL}/admin/documents/upload`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: formData,
  });
  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const err = await res.json();
      if (err.detail) errorDetail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
    } catch {}
    throw new ApiError(res.status, errorDetail);
  }
  return await res.json();
}


