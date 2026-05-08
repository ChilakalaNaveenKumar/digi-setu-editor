/**
 * Model-picker catalogue.
 *
 * `available` per model is filtered server-side against the user's plan
 * so the dropdown can render locked entries with an "Upgrade" hint
 * instead of just hiding them.
 */

import { apiJson, apiPatch } from "./client";
import type { ModelInfo, SessionRecord } from "./types";

export interface ModelsResponse {
  default: string;
  plan: string;
  models: ModelInfo[];
}

export function listModels(): Promise<ModelsResponse> {
  return apiJson("/api/models");
}

export function setSessionModel(sid: string, modelId: string): Promise<SessionRecord> {
  return apiPatch(`/api/sessions/${encodeURIComponent(sid)}/model`, { model: modelId });
}
