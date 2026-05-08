/**
 * permission.ts — per-tool-call user approval gate for pi.
 *
 * Loaded into every spawned pi via `--extension ./extensions/permission.ts`.
 * Subscribes to the `tool_call` event; depending on PI_PERMISSION_MODE and
 * the tool being invoked, either:
 *   - silently allows (read/grep/find/ls, or mode=auto, or session-allow cached)
 *   - silently denies (session-deny cached)
 *   - asks the user via ctx.ui.select with a magic-prefixed title that the
 *     backend recognises and translates into a `permission_request` WS event
 *
 * The user's answer is one of:
 *   - "allow_once"     — let this call through, ask again next time
 *   - "allow_session"  — remember (tool + arg-fingerprint), allow without
 *                        prompting for the rest of this pi process's life
 *   - "deny_once"      — block this call, ask again next time
 *   - "deny_session"   — block this call AND remember + auto-deny going forward
 *
 * The "intent" shown alongside the tool args is the most recent assistant
 * text we've observed via `message_update`, so the user knows the LLM's
 * reasoning instead of just a naked command.
 *
 * NOTE: This extension is a SECONDARY safety layer. The deterministic
 * blocklist in services/policy.py runs in the backend and can hard-deny
 * commands before they ever reach the user (sudo, metadata IP, curl|sh).
 * This extension covers the gray-area cases where intent matters and only
 * the human can decide.
 */

import { promises as fs, readFileSync } from "node:fs";
import path from "node:path";
import type {
	ExtensionAPI,
	ToolCallEvent,
	ToolCallEventResult,
} from "@mariozechner/pi-coding-agent";

// ── Configuration ───────────────────────────────────────────────────────────

type Mode = "auto" | "approve_risky" | "approve_all";

function parseMode(raw: string | undefined): Mode | undefined {
	if (!raw) return undefined;
	const v = raw.trim().toLowerCase();
	if (v === "auto" || v === "approve_risky" || v === "approve_all") return v;
	return undefined;
}

// Spawn-time fallback. Used when the live file is missing/unreadable.
const SPAWN_MODE: Mode = (() => {
	const m = parseMode(process.env.PI_PERMISSION_MODE);
	if (m) return m;
	if (process.env.PI_PERMISSION_MODE) {
		console.error(
			`[permission] unknown PI_PERMISSION_MODE=${process.env.PI_PERMISSION_MODE}, ` +
				"falling back to approve_risky",
		);
	}
	return "approve_risky";
})();

// Live file the backend updates whenever the user flips the picker. Single
// line, one mode token. We read it synchronously on every tool_call — the
// file is tiny (~16 bytes) and tool_call events fire at most a few times per
// second, so the cost is dwarfed by the LLM round-trip we're gating.
const MODE_FILE = process.env.PI_PERMISSION_MODE_FILE;

function currentMode(): Mode {
	if (!MODE_FILE) return SPAWN_MODE;
	try {
		return parseMode(readFileSync(MODE_FILE, "utf-8")) ?? SPAWN_MODE;
	} catch {
		// File doesn't exist yet, or transient I/O error. The spawn-time
		// value is still authoritative until the backend (re)writes it.
		return SPAWN_MODE;
	}
}

const TIMEOUT_MS = (() => {
	const n = Number(process.env.PI_PERMISSION_TIMEOUT_MS || "120000");
	return Number.isFinite(n) && n > 0 ? n : 120_000;
})();

/** Tools that are always safe to run without asking. Read-only filesystem ops. */
const SAFE_TOOLS: ReadonlySet<string> = new Set(["read", "grep", "find", "ls"]);

/** Tools that always require approval in approve_risky mode. */
const RISKY_TOOLS: ReadonlySet<string> = new Set([
	"bash",
	"write",
	"edit",
	"process",
	"process_start",
]);

/** Magic title prefix the backend looks for to know this is a permission select
 *  (vs. some other extension's UI request). The payload that follows is the
 *  JSON the frontend modal renders. Keep this in sync with chat_ws.py. */
const PERMISSION_PREFIX = "[pi-permission]";

// ── Module-level state (one set per pi process / one chat session) ──────────

const allowSession = new Set<string>();
const denySession = new Set<string>();
let lastAssistantText = "";

// ── Helpers ─────────────────────────────────────────────────────────────────

function fingerprint(toolName: string, input: Record<string, unknown>): string {
	if (toolName === "bash") {
		return `bash::${String(input.command ?? "")}`;
	}
	if (toolName === "write" || toolName === "edit") {
		return `${toolName}::${String(input.file_path ?? input.path ?? "")}`;
	}
	if (toolName === "process" || toolName === "process_start") {
		return `${toolName}::${String(input.command ?? input.argv ?? "")}`;
	}
	try {
		const argHash = JSON.stringify(input).slice(0, 200);
		return `${toolName}::${argHash}`;
	} catch {
		return `${toolName}::<unhashable>`;
	}
}

async function buildDiffPreview(
	toolName: string,
	input: Record<string, unknown>,
): Promise<{ kind: "diff"; oldText: string; newText: string; filePath: string } | undefined> {
	const filePath = String(input.file_path ?? input.path ?? "");
	if (!filePath) return undefined;
	const abs = path.isAbsolute(filePath) ? filePath : path.join(process.cwd(), filePath);
	let oldText = "";
	try {
		oldText = await fs.readFile(abs, "utf-8");
	} catch {
		// File doesn't exist yet — preview is "new file" with empty oldText.
	}
	let newText = "";
	if (toolName === "write") {
		newText = String(input.content ?? "");
	} else if (toolName === "edit") {
		// Pi's edit tool replaces old_string with new_string. We can simulate
		// the result for preview purposes; we don't try to be 100% accurate
		// (e.g. multiple matches), just show the substitution.
		const oldStr = String(input.old_string ?? "");
		const newStr = String(input.new_string ?? "");
		if (oldStr && oldText.includes(oldStr)) {
			newText = oldText.split(oldStr).join(newStr);
		} else {
			newText = oldText; // edit will fail anyway; show no-op preview
		}
	}
	return { kind: "diff", oldText, newText, filePath };
}

interface PermissionPayload {
	v: 1;
	tool: string;
	tool_call_id: string;
	input: Record<string, unknown>;
	intent: string;
	preview?: { kind: "diff"; oldText: string; newText: string; filePath: string };
	mode: Mode;
}

function shouldPrompt(toolName: string, mode: Mode): boolean {
	if (mode === "auto") return false;
	if (mode === "approve_all") return !SAFE_TOOLS.has(toolName);
	// approve_risky
	return RISKY_TOOLS.has(toolName);
}

// ── Extension factory ───────────────────────────────────────────────────────

export default function (pi: ExtensionAPI): void {
	console.error(
		`[permission] loaded spawn_mode=${SPAWN_MODE} live_file=${MODE_FILE ?? "<none>"} ` +
			`timeout=${TIMEOUT_MS}ms ` +
			`(set PI_PERMISSION_MODE=auto|approve_risky|approve_all to change spawn default)`,
	);

	pi.on("message_update", (evt) => {
		// Track the most recent assistant text so we can show it as "intent"
		// alongside any tool call. We only care about the visible text content.
		try {
			const message = (evt as { message?: { content?: unknown } }).message;
			const content = message?.content;
			if (!Array.isArray(content)) return;
			const parts: string[] = [];
			for (const block of content) {
				if (block && typeof block === "object" && "text" in block) {
					const t = (block as { text?: unknown }).text;
					if (typeof t === "string") parts.push(t);
				}
			}
			if (parts.length > 0) lastAssistantText = parts.join("\n").trim();
		} catch {
			// Best effort; never let this crash the pump.
		}
	});

	pi.on("tool_call", async (event: ToolCallEvent, ctx): Promise<ToolCallEventResult | undefined> => {
		const toolName = event.toolName;
		const input = (event.input ?? {}) as Record<string, unknown>;
		const fp = fingerprint(toolName, input);

		// Persistent session decisions short-circuit everything.
		if (denySession.has(fp)) {
			return { block: true, reason: "user previously denied this command for the session" };
		}
		if (allowSession.has(fp)) {
			return undefined;
		}

		// Re-read the live mode file every tool call. This is what makes
		// the picker in the browser apply to the running pi — the user
		// flips approve_risky → auto and the very next tool stops
		// prompting, no respawn needed.
		const mode = currentMode();

		if (!shouldPrompt(toolName, mode)) {
			return undefined; // mode=auto, or read/grep/find/ls
		}

		// In RPC mode hasUI is true (the host translates ctx.ui.* into RPC events).
		// In print/json mode it's false — fall back to allow with a warning so a
		// non-interactive pi run doesn't deadlock.
		if (!ctx.hasUI) {
			console.error(
				`[permission] no UI available — auto-allowing ${toolName} (${fp})`,
			);
			return undefined;
		}

		const preview =
			toolName === "write" || toolName === "edit"
				? await buildDiffPreview(toolName, input).catch(() => undefined)
				: undefined;

		const payload: PermissionPayload = {
			v: 1,
			tool: toolName,
			tool_call_id: event.toolCallId,
			input,
			intent: lastAssistantText.slice(0, 4000),
			preview,
			mode,
		};

		// We pack the structured payload into the title (the backend strips the
		// prefix and parses the JSON before forwarding to the browser). The
		// `message` field stays human-readable for any non-web client that
		// surfaces the dialog as a plain text confirm.
		const title = `${PERMISSION_PREFIX}${JSON.stringify(payload)}`;
		const message = `pi wants to call \`${toolName}\` with arguments:\n${JSON.stringify(input, null, 2)}`;

		const choice = await ctx.ui.select(
			title,
			["allow_once", "allow_session", "deny_once", "deny_session"],
			{ timeout: TIMEOUT_MS },
		);

		// Anything other than an explicit allow_* decision is treated as a deny.
		// Undefined (cancelled / timed out) defaults to deny — fail safe.
		if (choice === "allow_once") {
			return undefined;
		}
		if (choice === "allow_session") {
			allowSession.add(fp);
			return undefined;
		}
		if (choice === "deny_session") {
			denySession.add(fp);
			return { block: true, reason: "user denied (session)" };
		}
		return { block: true, reason: choice === "deny_once" ? "user denied" : "user did not respond in time" };
	});
}
