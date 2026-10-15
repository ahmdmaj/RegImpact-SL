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
}

export interface StructuredImpactReport {
  as_at_date: string;
  total_rules_evaluated: intOrNumber;
  applicable_rules_count: intOrNumber;
  conditional_rules_count: intOrNumber;
  not_applicable_rules_count: intOrNumber;
  unsupported_rules_count: intOrNumber;
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
      headers: { "Content-Type": "application/json" },
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
    headers: { "Content-Type": "application/json" },
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
    headers: { "Content-Type": "application/json" },
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
