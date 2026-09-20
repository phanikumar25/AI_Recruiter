import type {
  FitRubric,
  FeedbackItem,
  ObjectiveFilters,
  SearchState,
  WorkflowResponse,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function createSearch(query: string) {
  return request<WorkflowResponse>("/api/searches", {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}

export function reviewSpec(
  searchId: string,
  filters: ObjectiveFilters,
  rubric: FitRubric,
) {
  return request<WorkflowResponse>(`/api/searches/${searchId}/spec-review`, {
    method: "POST",
    body: JSON.stringify({ filters, rubric }),
  });
}

export function reviewResults(
  searchId: string,
  action: "refine" | "freeze",
  feedback: FeedbackItem[],
  overallFeedback: string,
) {
  return request<WorkflowResponse>(`/api/searches/${searchId}/result-review`, {
    method: "POST",
    body: JSON.stringify({
      action,
      feedback,
      overall_feedback: overallFeedback,
    }),
  });
}

export function getSearch(searchId: string) {
  return request<{ state: SearchState }>(`/api/searches/${searchId}`);
}
