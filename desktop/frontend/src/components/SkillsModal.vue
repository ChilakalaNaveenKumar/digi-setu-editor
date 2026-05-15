<!--
  SkillsModal — manage skill documents (desktop).

  Mirrors the web copy but adds an "Open skills folder" button that
  bounces through a Tauri command to reveal the on-disk skills
  directory in Finder/Explorer. The web edition can't do this (skills
  live in DATA_ROOT inside the container) so the button is hidden
  there entirely.

  Skills are markdown files (`SKILL.md` with YAML front-matter) loaded
  by `desktop/backend/services/skills.py`. The user folder lives at
  `~/.digi-setu/skills/<name>/SKILL.md`; bundled skills come from the
  packaged `.pi/skills/` directory and are read-only.
-->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Icon } from "@iconify/vue";

import { apiDelete, apiJson, apiPost } from "../api/client";
import { useUiStore } from "../stores/ui";
import { useWorkspaceStore } from "../stores/workspace";

interface SkillSummary {
  name: string;
  description: string;
  source: "global" | "workspace";
  auto: string;
  triggers: string[];
}

defineEmits<{ close: [] }>();

const ui = useUiStore();
const workspace = useWorkspaceStore();

const loading = ref(true);
const saving = ref(false);
const openingFolder = ref(false);
const skills = ref<SkillSummary[]>([]);

const showForm = ref(false);
const draftName = ref("");
const draftBody = ref("");

// "Workspace" skills are scoped to the active project — they include
// the auto-seeded `compile-loop` skill that the env probe regenerates
// from the user's actual machine. "Global" skills live under
// `~/.digi-setu/skills/` and are shared across every workspace. The
// upload form below only writes globals; workspace skills are managed
// by dropping `SKILL.md` files into the per-project `.digi-setu/skills/`
// folder by hand (or by the env probe).
const workspaceSkills = computed(() => skills.value.filter((s) => s.source === "workspace"));
const globalSkills = computed(() => skills.value.filter((s) => s.source === "global"));

async function refresh(): Promise<void> {
  loading.value = true;
  try {
    // Include the active workspace so workspace-scoped skills show up
    // alongside globals. Falls back to globals-only when the user
    // hasn't picked a workspace yet.
    const qs = workspace.activeId
      ? `?workspace_id=${encodeURIComponent(workspace.activeId)}`
      : "";
    const r = await apiJson<{ skills: SkillSummary[] }>(`/api/skills${qs}`);
    skills.value = r.skills || [];
  } catch (exc) {
    ui.toastError("Load skills", exc);
  } finally {
    loading.value = false;
  }
}

async function onUpload(): Promise<void> {
  const name = draftName.value.trim();
  const body = draftBody.value.trim();
  if (!name || !body) {
    ui.toastError("Upload skill", new Error("Name and body are both required"));
    return;
  }
  saving.value = true;
  try {
    await apiPost<{ ok: boolean }>("/api/skills", { name, body });
    showForm.value = false;
    draftName.value = "";
    draftBody.value = "";
    await refresh();
  } catch (exc) {
    ui.toastError("Upload skill", exc);
  } finally {
    saving.value = false;
  }
}

async function onDelete(skill: SkillSummary): Promise<void> {
  // Only globals (the writable dir) can be deleted via REST. Workspace
  // skills live next to the user's project files; nuking them via a
  // modal would be too easy to fat-finger, so the "Open folder" button
  // is the supported path for those.
  if (skill.source !== "global") return;
  if (!window.confirm(`Delete skill "${skill.name}"? This cannot be undone.`)) return;
  try {
    await apiDelete(`/api/skills/${encodeURIComponent(skill.name)}`);
    await refresh();
  } catch (exc) {
    ui.toastError("Delete skill", exc);
  }
}

// Tauri reveal-in-Finder. We call the backend's `/api/skills/open_folder`
// route which delegates to the OS file manager. Doing it server-side
// keeps the path resolution (DATA_ROOT) on the side that knows where
// the folder actually is — the frontend never needs to know, which
// also means a future move of the skills directory doesn't break
// this button.
async function openSkillsFolder(): Promise<void> {
  openingFolder.value = true;
  try {
    await apiPost<{ ok: boolean }>("/api/skills/open_folder", {});
  } catch (exc) {
    ui.toastError("Open skills folder", exc);
  } finally {
    openingFolder.value = false;
  }
}

const sampleBody = `---
name: my-style
description: House brand colours + tone for design work.
auto: surface
triggers: ["report", "deck", "slides"]
---
When generating documents for me, prefer:
- Navy (#0a2540) for headings
- Concise tone, no hedging
- 11pt body, 9pt captions
`;

function fillSample(): void {
  if (!draftName.value) draftName.value = "my-style";
  if (!draftBody.value) draftBody.value = sampleBody;
}

onMounted(() => {
  void refresh();
});
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
    @click.self="$emit('close')"
  >
    <div class="flex w-full max-w-2xl flex-col rounded-lg border border-border bg-background shadow-xl">
      <header class="flex items-center justify-between border-b border-border px-5 py-3">
        <div>
          <h2 class="text-lead font-semibold">Skills</h2>
          <p class="text-caption text-muted-foreground">
            Markdown documents that extend Digi Setu's behaviour.
            Auto-loaded when their triggers match, or referenced
            explicitly with <code class="rounded bg-muted px-1">@skill-name</code> in the composer.
          </p>
        </div>
        <button
          type="button"
          class="rounded px-2 py-1 text-lead text-muted-foreground hover:bg-muted"
          aria-label="close"
          @click="$emit('close')"
        >
          ✕
        </button>
      </header>

      <div class="flex-1 overflow-y-auto px-5 py-4">
        <div v-if="loading" class="py-8 text-center text-muted-foreground">Loading…</div>

        <div v-else>
          <section v-if="workspaceSkills.length > 0" class="mb-5">
            <h3 class="mb-2 font-mono text-caption uppercase tracking-wide text-muted-foreground">
              Workspace · auto-generated + per-project
            </h3>
            <ul class="space-y-1.5">
              <li
                v-for="sk in workspaceSkills"
                :key="sk.name"
                class="rounded border border-border bg-card px-3 py-2"
              >
                <div class="flex items-center gap-2">
                  <code class="text-body font-semibold text-foreground">@{{ sk.name }}</code>
                  <span
                    v-if="sk.auto"
                    class="rounded-full bg-primary/10 px-1.5 py-0.5 text-caption text-primary"
                    :title="`auto-loads on ${sk.auto === 'flow_entry' ? 'every turn' : 'matching triggers'}`"
                  >
                    {{ sk.auto === "flow_entry" ? "always" : "on trigger" }}
                  </span>
                </div>
                <p v-if="sk.description" class="mt-1 text-body leading-snug text-muted-foreground">
                  {{ sk.description }}
                </p>
                <p v-if="sk.triggers.length > 0" class="mt-1 text-caption text-muted-foreground">
                  triggers:
                  <code v-for="t in sk.triggers" :key="t" class="ml-1 rounded bg-muted px-1">{{ t }}</code>
                </p>
              </li>
            </ul>
          </section>

          <section class="mb-3">
            <div class="mb-2 flex items-center justify-between">
              <h3 class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
                Global skills · {{ globalSkills.length }}
              </h3>
              <button
                type="button"
                class="inline-flex items-center gap-1 rounded border border-border bg-background px-2 py-0.5 text-caption text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
                :disabled="openingFolder"
                title="Reveal the skills folder in Finder/Explorer"
                @click="openSkillsFolder"
              >
                <Icon icon="codicon:folder-opened" class="h-3.5 w-3.5" />
                Open folder
              </button>
            </div>
            <ul v-if="globalSkills.length > 0" class="space-y-1.5">
              <li
                v-for="sk in globalSkills"
                :key="sk.name"
                class="rounded border border-border bg-card px-3 py-2"
              >
                <div class="flex items-center justify-between gap-2">
                  <div class="min-w-0 flex-1">
                    <div class="flex items-center gap-2">
                      <code class="text-body font-semibold text-foreground">@{{ sk.name }}</code>
                      <span
                        v-if="sk.auto"
                        class="rounded-full bg-primary/10 px-1.5 py-0.5 text-caption text-primary"
                      >
                        {{ sk.auto === "flow_entry" ? "always" : "on trigger" }}
                      </span>
                    </div>
                    <p v-if="sk.description" class="mt-1 text-body leading-snug text-muted-foreground">
                      {{ sk.description }}
                    </p>
                    <p v-if="sk.triggers.length > 0" class="mt-1 text-caption text-muted-foreground">
                      triggers:
                      <code v-for="t in sk.triggers" :key="t" class="ml-1 rounded bg-muted px-1">{{ t }}</code>
                    </p>
                  </div>
                  <button
                    type="button"
                    class="shrink-0 rounded p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                    :title="`Delete ${sk.name}`"
                    @click="onDelete(sk)"
                  >
                    <Icon icon="codicon:trash" class="h-4 w-4" />
                  </button>
                </div>
              </li>
            </ul>
            <p v-else class="rounded border border-dashed border-border px-3 py-3 text-caption text-muted-foreground">
              You haven't uploaded any skills yet. Click "Upload skill"
              below, or drop a <code>SKILL.md</code> into the folder you
              just opened and refresh.
            </p>
          </section>

          <div v-if="!showForm" class="text-center">
            <button
              type="button"
              class="inline-flex items-center gap-1.5 rounded border border-border bg-card px-3 py-1.5 text-body hover:bg-muted"
              @click="showForm = true"
            >
              <Icon icon="codicon:add" class="h-3.5 w-3.5" />
              Upload skill
            </button>
          </div>

          <div
            v-else
            class="rounded-md border border-primary/40 bg-card px-3 py-3 shadow-sm"
          >
            <div class="mb-2 flex items-center justify-between">
              <h4 class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
                New skill
              </h4>
              <button
                type="button"
                class="rounded px-1.5 py-0.5 text-caption text-muted-foreground hover:bg-muted hover:text-foreground"
                @click="fillSample"
              >
                Fill with example
              </button>
            </div>
            <label class="block">
              <span class="block font-mono text-caption text-muted-foreground">Name</span>
              <input
                v-model="draftName"
                type="text"
                placeholder="e.g. my-style"
                maxlength="64"
                class="mt-1 w-full rounded border border-border bg-background px-2 py-1 text-body focus:border-primary focus:outline-none"
              />
              <span class="mt-0.5 block text-caption text-muted-foreground">
                Lowercase letters / digits / hyphens. Referenced as
                <code>@{{ draftName || "name" }}</code>.
              </span>
            </label>

            <label class="mt-3 block">
              <span class="block font-mono text-caption text-muted-foreground">SKILL.md body</span>
              <textarea
                v-model="draftBody"
                rows="10"
                placeholder="---&#10;name: my-style&#10;description: Short tagline&#10;auto: surface&#10;triggers: [&quot;keyword&quot;]&#10;---&#10;Instructions for the AI…"
                class="mt-1 w-full resize-y rounded border border-border bg-background px-2 py-1 font-mono text-body focus:border-primary focus:outline-none"
              />
              <span class="mt-0.5 block text-caption text-muted-foreground">
                YAML front-matter between <code>---</code> markers,
                then the body. <code>auto: flow_entry</code> loads on
                every turn; <code>auto: surface</code> loads when any
                <code>triggers</code> substring matches the prompt.
              </span>
            </label>

            <div class="mt-3 flex items-center justify-end gap-2">
              <button
                type="button"
                class="rounded px-3 py-1 text-body text-muted-foreground hover:bg-muted hover:text-foreground"
                :disabled="saving"
                @click="showForm = false"
              >
                Cancel
              </button>
              <button
                type="button"
                class="rounded bg-primary px-3 py-1 text-body text-primary-foreground disabled:opacity-50"
                :disabled="saving || !draftName.trim() || !draftBody.trim()"
                @click="onUpload"
              >
                {{ saving ? "Saving…" : "Save skill" }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <footer class="border-t border-border px-5 py-2.5 text-caption text-muted-foreground">
        Tip: type <code class="rounded bg-muted px-1">@</code> in the
        composer to pick a skill on demand. Bundled skills always load
        first; user skills override by name when both exist.
      </footer>
    </div>
  </div>
</template>
