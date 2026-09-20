export type FeedbackDecision = "accept" | "reject" | "maybe";

export interface ObjectiveFilters {
  required_skills: string[];
  preferred_skills: string[];
  min_years_experience: number | null;
  max_years_experience: number | null;
  locations: string[];
  company_types: string[];
  past_company_keywords: string[];
}

export interface RubricCriterion {
  name: string;
  description: string;
  weight: number;
}

export interface FitRubric {
  criteria: RubricCriterion[];
}

export interface CandidateProfile {
  id: string;
  name: string;
  current_title: string;
  years_experience: number;
  location: string;
  current_company: string;
  current_company_type: string;
  skills: string[];
  past_companies: Array<{
    company: string;
    company_type: string;
    title: string;
    years: number;
  }>;
  education: string;
  summary: string;
}

export interface CandidateScore {
  candidate_id: string;
  score: number;
  strengths: string[];
  concerns: string[];
  explanation: string;
  evidence: string[];
}

export interface FilterDiagnostics {
  total_candidates: number;
  matched_candidates: number;
  excluded_candidates: number;
  exclusion_reasons: Record<string, number>;
}

export interface SearchState {
  search_id: string;
  stage: string;
  original_query: string;
  filters: ObjectiveFilters | null;
  rubric: FitRubric | null;
  candidate_profiles: CandidateProfile[];
  results: CandidateScore[];
  diagnostics: FilterDiagnostics | null;
  refinement_round: number;
  changes: string[];
  frozen: boolean;
  error: string | null;
}

export interface InterruptPayload {
  type: "review_spec" | "review_results";
  message: string;
  filters?: ObjectiveFilters;
  rubric?: FitRubric;
  results?: CandidateScore[];
  diagnostics?: FilterDiagnostics | null;
  refinement_round?: number;
  changes?: string[];
}

export interface WorkflowResponse {
  status: "interrupted" | "completed";
  interrupt: InterruptPayload | null;
  state: SearchState;
}

export interface FeedbackItem {
  candidate_id: string;
  decision: FeedbackDecision;
  comment: string;
}
