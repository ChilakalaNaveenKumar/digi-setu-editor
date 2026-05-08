import { apiPost } from "./client";

export interface FeedbackPayload {
  message: string;
  category?: "bug" | "idea" | "other";
  contact_email?: string | null;
}

export interface FeedbackResponse {
  ok: boolean;
  destination: string;
}

export function submitFeedback(payload: FeedbackPayload): Promise<FeedbackResponse> {
  return apiPost<FeedbackResponse>("/api/feedback", payload);
}
