<!--
  SubagentToolCard — dedicated card for pi's bundled `subagent` extension.

  Source: pi-mono-main/packages/coding-agent/examples/extensions/subagent/.
  The extension spawns isolated `pi` child processes for scoped work
  (so a "scan this whole codebase" task can't trash the main context
  window). Result shape from index.ts ~L716:

      {
        mode: "single" | "chain" | "parallel",
        results: [
          {
            agent:       string,   // sub-agent name
            agentSource: string,   // "builtin" | "user" | "project"
            task:        string,   // the prompt the parent gave it
            exitCode:    number,   // 0 = ok, !=0 = failed, -1 = still running
            stopReason?: string,
            errorMessage?: string,
            usage: { input, output, cacheRead, cacheWrite, cost, turns },
            model:       string,
            messages:    [...],    // full transcript — we don't render
          },
          …
        ]
      }

  We mirror pi's TUI rendering verbatim where it makes sense:
    - ✓ green / ✗ red per child agent
    - "{n}/{total} done, {running} running" header for parallel
    - "{n}/{total} steps" header for chain
    - Single shows just the agent name + final output

  We collapse the full transcript by default; expand to see each agent's
  task + final output.
-->
<script setup lang="ts">
import { Icon } from "@iconify/vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import { useSubagentPanelStore } from "../../stores/subagent-panel";
import type { ToolCall } from "../../types/rpc";

const props = defineProps<{ call: ToolCall }>();

// Side-drawer integration. The card now has TWO interactions:
//   - Click anywhere on the header → open the live drawer (this is
//     what the user wants by default — see live transcript / tabs /
//     stop button in the right column).
//   - Click the small chevron → expand the legacy inline preview
//     (final-output snippet). We keep the inline view because for
//     completed runs sometimes you just want a glance without
//     opening the drawer.
//
// The drawer is single-instance: clicking the same card twice toggles
// it closed (panelStore.toggle).
const panelStore = useSubagentPanelStore();
const { openCallId } = storeToRefs(panelStore);
const isPanelOpen = computed(() => openCallId.value === props.call.id);

interface SubagentResult {
  agent: string;
  agentSource?: string;
  task: string;
  exitCode: number;
  stopReason?: string;
  errorMessage?: string;
  usage?: { input?: number; output?: number; cost?: number; turns?: number };
  model?: string;
  /** Final markdown the sub-agent emitted (we extract from `messages`). */
  finalOutput?: string;
}

interface SubagentDetails {
  mode: "single" | "chain" | "parallel";
  results: SubagentResult[];
}

const details = computed<SubagentDetails | null>(() => {
  const d = props.call.result?.details as SubagentDetails | undefined;
  if (!d || !Array.isArray(d.results)) return null;
  return d;
});

const args = computed(
  () =>
    props.call.args as
      | {
          agent?: string;
          task?: string;
          tasks?: Array<{ agent: string; task: string }>;
        }
      | undefined,
);

const headerState = computed<"pending" | "running" | "success" | "error">(() => {
  if (props.call.status === "pending" || props.call.status === "running") return props.call.status;
  if (props.call.status === "error") return "error";
  const d = details.value;
  if (!d) return "success";
  // Any child still running (-1) keeps us in "running"; any failure flips us to error.
  if (d.results.some((r) => r.exitCode === -1)) return "running";
  if (d.results.some((r) => r.exitCode !== 0)) return "error";
  return "success";
});

const headerIconClass = computed(() => {
  switch (headerState.value) {
    case "pending":
      return "text-muted-foreground";
    case "running":
      return "text-primary";
    case "success":
      return "text-success";
    case "error":
      return "text-destructive";
  }
});

/** Headline text — mirrors pi's TUI renderer one-liners. */
const summary = computed(() => {
  const d = details.value;
  if (!d) {
    if (args.value?.tasks && args.value.tasks.length > 0) {
      return `parallel · ${args.value.tasks.length} agents`;
    }
    if (args.value?.agent) return args.value.agent;
    return "spawning…";
  }
  const total = d.results.length;
  const succeeded = d.results.filter((r) => r.exitCode === 0).length;
  const failed = d.results.filter((r) => r.exitCode > 0).length;
  const running = d.results.filter((r) => r.exitCode === -1).length;

  if (d.mode === "single") {
    const r = d.results[0];
    return r ? r.agent : "(no agent)";
  }
  if (d.mode === "chain") {
    return `chain · ${succeeded}/${total} steps`;
  }
  if (running > 0) return `parallel · ${succeeded + failed}/${total} done, ${running} running`;
  return `parallel · ${succeeded}/${total} done${failed > 0 ? `, ${failed} failed` : ""}`;
});

// Collapsed by default — subagent results often include long task
// strings and transcripts; expanded cards eat half the chat.
const expanded = ref(false);

function childStatusIcon(r: SubagentResult): string {
  if (r.exitCode === -1) return "codicon:loading";
  if (r.exitCode === 0) return "codicon:check";
  return "codicon:close";
}

function childStatusClass(r: SubagentResult): string {
  if (r.exitCode === -1) return "text-primary animate-spin";
  if (r.exitCode === 0) return "text-success";
  return "text-destructive";
}

function previewTask(task: string, limit = 100): string {
  if (task.length <= limit) return task;
  return task.slice(0, limit) + "…";
}

function fmtCost(r: SubagentResult): string {
  const c = r.usage?.cost;
  if (typeof c !== "number" || c === 0) return "";
  if (c < 0.01) return `$${(c * 1000).toFixed(2)}m`;
  return `$${c.toFixed(2)}`;
}
</script>

<template>
  <div
    :class="[
      'group my-2 rounded-md border bg-card px-3 py-2 text-body shadow-sm transition-colors',
      isPanelOpen ? 'border-primary/60 ring-1 ring-primary/30' : 'border-border hover:border-border/80',
    ]"
  >
    <button
      type="button"
      class="flex w-full items-center gap-2 text-left"
      :aria-pressed="isPanelOpen"
      :title="isPanelOpen ? 'Click to close live panel' : 'Click to open live transcript'"
      @click="panelStore.toggle(call.id)"
    >
      <Icon icon="codicon:organization" :class="['h-4 w-4 shrink-0', headerIconClass]" />
      <span class="font-mono font-semibold text-foreground">subagent</span>
      <span class="text-caption text-muted-foreground">·</span>
      <span class="flex-1 truncate text-caption text-muted-foreground">{{ summary }}</span>

      <Icon
        v-if="headerState === 'running' || headerState === 'pending'"
        icon="codicon:loading"
        class="h-3.5 w-3.5 shrink-0 animate-spin text-muted-foreground"
      />

      <Icon
        :icon="isPanelOpen ? 'codicon:chevron-left' : 'codicon:arrow-right'"
        :class="['h-3.5 w-3.5 shrink-0', isPanelOpen ? 'text-primary' : 'text-muted-foreground']"
      />

      <span
        v-if="details"
        role="button"
        :aria-label="expanded ? 'Collapse inline preview' : 'Expand inline preview'"
        :title="expanded ? 'Collapse inline preview' : 'Expand inline preview'"
        class="ml-0.5 inline-flex h-5 w-5 items-center justify-center rounded text-muted-foreground hover:bg-muted hover:text-foreground"
        @click.stop="expanded = !expanded"
      >
        <Icon
          :icon="expanded ? 'codicon:chevron-up' : 'codicon:chevron-down'"
          class="h-3.5 w-3.5"
        />
      </span>
    </button>

    <div v-if="expanded && details" class="mt-2 space-y-2">
      <div
        v-for="(r, idx) in details.results"
        :key="idx"
        class="rounded border border-border/60 bg-background/50 px-2.5 py-1.5"
      >
        <div class="flex items-center gap-2 text-body">
          <Icon :icon="childStatusIcon(r)" :class="['h-3.5 w-3.5 shrink-0', childStatusClass(r)]" />
          <span
            class="font-mono font-semibold text-foreground"
            :title="r.usage ? `${fmtCost(r)} · ${r.usage.turns ?? 0} turns · ${r.model ?? ''}` : undefined"
          >{{ r.agent }}</span>
          <span
            v-if="r.agentSource"
            class="rounded-sm bg-muted px-1.5 py-0.5 text-caption text-muted-foreground"
          >{{ r.agentSource }}</span>
          <span
            v-if="r.stopReason && r.exitCode !== 0"
            class="rounded-sm bg-destructive/15 px-1.5 py-0.5 text-caption text-destructive"
          >{{ r.stopReason }}</span>
          <span class="flex-1"></span>
          <!--
            Cost + turns are intentionally NOT shown on the inline child
            row. Stamping "$0.97" + "5t" on every line just reads as
            alarming noise — especially across 4 parallel children where
            the eye totals them automatically. The same numbers live in
            the SubagentLivePanel footer (one canonical place per agent,
            visible only when the user clicks in). A hover tooltip on
            the agent name still surfaces them for power users.
          -->
        </div>

        <div class="mt-1 text-caption text-muted-foreground">
          <span class="select-none">task: </span>{{ previewTask(r.task) }}
        </div>

        <div
          v-if="r.errorMessage"
          class="mt-1 rounded border border-destructive/30 bg-destructive/10 px-2 py-1 text-caption text-destructive"
        >
          {{ r.errorMessage }}
        </div>

        <div
          v-if="r.finalOutput"
          class="mt-1 max-h-40 overflow-auto whitespace-pre-wrap break-words rounded bg-background px-2 py-1 text-caption leading-snug text-foreground"
        >{{ r.finalOutput }}</div>
      </div>
    </div>
  </div>
</template>
