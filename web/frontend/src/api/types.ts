/**
 * Wire-format types shared between api/ modules and stores/.
 *
 * Mirrors the pydantic models in `backend/models/`. If you change one
 * side, change the other — there's no codegen yet.
 */

export type DeployMode = "web" | "desktop";

export interface WorkspaceRecord {
  id: string;
  mode: DeployMode;
  path: string;
  name: string;
  created_at: string;
  last_used: string;
}

export interface SessionRecord {
  id: string;
  workspace_id: string;
  title: string;
  /** Pinned model id (matches `ModelInfo.id`). null = "use the user's
   * default for their plan at spawn time". */
  model: string | null;
  created_at: string;
  last_used: string;
}

export interface ModelInfo {
  id: string;
  name: string;
  family: "anthropic" | "google";
  context_window: number;
  reasoning: boolean;
  /** Cheapest plan tier that can pick this model. */
  min_plan: "free" | "starter" | "pro" | "enterprise";
  /** True if the current user's plan permits this model. */
  available: boolean;
  blurb: string;
  cost_per_mtok_input: number;
  cost_per_mtok_output: number;
}

export interface PlanInfo {
  id: "free" | "starter" | "pro" | "enterprise";
  label: string;
  monthly_price_usd: number;
  monthly_credit_usd: number;
  stripe_price_id: string;
  description: string;
}

export interface CreditSnapshot {
  month: string;
  plan: {
    id: string;
    label: string;
    monthly_price_usd: number;
    monthly_credit_usd: number;
  };
  spent_usd: number;
  remaining_usd: number;
  remaining_pct: number;
  prompts: number;
  stripe_customer_id: string | null;
}

export interface FileEntry {
  path: string;
  is_dir: boolean;
  size: number;
  mtime: number;
}

export interface FileContent {
  path: string;
  size: number;
  kind: "text" | "image" | "pdf" | "svg" | "audio" | "video" | "binary";
  binary: boolean;
  truncated: boolean;
  content: string;
  reason?: string;
}

export interface FsChangeEvent {
  kind: "created" | "modified" | "deleted" | "moved";
  path: string;
  is_dir: boolean;
  src?: string;
}

export interface ShellProfile {
  id: string;
  label: string;
  path: string;
  isDefault?: boolean;
}

export interface PtyTerminal {
  id: string;
  shell: string;
  cwd: string;
  cols: number;
  rows: number;
  closed?: boolean;
}

export interface BackgroundProcessInfo {
  id: string;
  name: string;
  command: string;
  pid: number;
  stdoutFile: string;
  stderrFile: string;
  startTime: number;
  status: string;
  exitCode: number | null;
  endTime?: number | null;
}
