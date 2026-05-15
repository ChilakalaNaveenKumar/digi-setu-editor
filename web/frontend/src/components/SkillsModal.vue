<!--
  SkillsModal — manage skill documents.

  Skills are markdown files (`SKILL.md` with YAML front-matter) that
  augment the chat system prompt either automatically (when their
  declared `triggers` match the user message) or on demand via
  `@skill-name` in the composer. The full resolution flow lives in
  `web/backend/services/skills.py`; this dialog just exposes the
  REST CRUD API to the user.

  Layout:

      ┌─────────────────────────────────────────────────┐
      │ Skills                                        ✕ │
      ├─────────────────────────────────────────────────┤
      │ Bundled · cannot be deleted                     │
      │  • compile-loop  — write/compile/render…        │
      │ Your skills                                     │
      │  • my-style      — house brand colours…   [del] │
      │                                                 │
      │ [+ Upload skill]                                │
      ├─────────────────────────────────────────────────┤
      │ Tip: in the composer, type @skill-name to load  │
      │ a skill on demand.                              │
      └─────────────────────────────────────────────────┘

  Why a modal and not a tab in ChatSettingsMenu:
    - The settings popover is 320×360 and already shows permission +
      credit. A skill list with upload form would push it past the
      viewport on small screens.
    - Skill upload involves a multi-line markdown textarea; a modal
      gives it the room it needs without the popover becoming a
      mini-IDE.
-->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Icon } from "@iconify/vue";

import { apiDelete, apiJson, apiPost } from "../api/client";
import { useUiStore } from "../stores/ui";

interface SkillSummary {
  name: string;
  description: string;
  source: "bundled" | "user";
  auto: string;
  triggers: string[];
}

defineEmits<{ close: [] }>();

const ui = useUiStore();

const loading = ref(true);
const saving = ref(false);
const skills = ref<SkillSummary[]>([]);

const showForm = ref(false);
const draftName = ref("");
const draftBody = ref("");

const bundled = computed(() => skills.value.filter((s) => s.source === "bundled"));
const userSkills = computed(() => skills.value.filter((s) => s.source === "user"));

async function refresh(): Promise<void> {
  loading.value = true;
  try {
    const r = await apiJson<{ skills: SkillSummary[] }>("/api/skills");
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
  if (skill.source !== "user") return;
  // Confirm so a stray click doesn't nuke a skill the user spent
  // time writing. The native confirm() is sufficient — no need to
  // ship a custom modal-in-modal.
  if (!window.confirm(`Delete skill "${skill.name}"? This cannot be undone.`)) return;
  try {
    await apiDelete(`/api/skills/${encodeURIComponent(skill.name)}`);
    await refresh();
  } catch (exc) {
    ui.toastError("Delete skill", exc);
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
            Markdown documents that extend pi's behaviour. Auto-loaded
            when their triggers match, or referenced explicitly with
            <code class="rounded bg-muted px-1">@skill-name</code> in the composer.
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
          <!-- Bundled skills (read-only) -->
          <section v-if="bundled.length > 0" class="mb-5">
            <h3 class="mb-2 font-mono text-caption uppercase tracking-wide text-muted-foreground">
              Bundled · read-only
            </h3>
            <ul class="space-y-1.5">
              <li
                v-for="sk in bundled"
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

          <!-- User skills -->
          <section class="mb-3">
            <h3 class="mb-2 font-mono text-caption uppercase tracking-wide text-muted-foreground">
              Your skills · {{ userSkills.length }}
            </h3>
            <ul v-if="userSkills.length > 0" class="space-y-1.5">
              <li
                v-for="sk in userSkills"
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
              below to add one.
            </p>
          </section>

          <!-- Upload form (collapsed by default) -->
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
