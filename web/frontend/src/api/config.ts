import { apiJson } from "./client";
import type { DeployMode } from "./types";

export interface ServerConfig {
  mode: DeployMode;
  /**
   * When false the SPA skips Clerk init entirely and behaves as if the
   * (synthetic) "dev" user is always signed in. Backend mirrors this.
   */
  auth_required: boolean;
  /**
   * Clerk frontend boot key. Empty in dev mode. We get it from the
   * server (not Vite env) so the same SPA bundle ships to staging
   * and prod without rebuilding.
   */
  clerk_publishable_key: string;
  /**
   * Desktop only: true when the user dropped their own AI provider
   * keys into ~/.digi-setu/.env. Skips login + hides Upgrade buttons.
   */
  byok_mode?: boolean;
  /**
   * Names of detected BYOK env vars (e.g. ["ANTHROPIC_API_KEY"]) so
   * the SPA's "using your own key" chip can show what's wired up.
   */
  byok_keys?: string[];
}

export function getConfig(): Promise<ServerConfig> {
  return apiJson<ServerConfig>("/api/config");
}
