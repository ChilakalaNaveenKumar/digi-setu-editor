<!--
  FeedbackModal — explicit, non-angled, transparent destination.

  The original feedback called out two specific UX bugs in the prior
  product:
    1. "Why make the Feedback windows slightly angled?" — the styling
       implied something silly was happening. We use a plain rectangle.
    2. "It was also not clear who this feedback is sent to" — we show
       the destination email as a literal string, not an icon, not a
       hover tooltip. The user knows exactly where it goes.

  We also renamed the primary action from "Send" to "Send feedback"
  so it doesn't read like a model prompt button.
-->
<script setup lang="ts">
import { ref } from "vue";

import { submitFeedback } from "../api/feedback";
import { useUiStore } from "../stores/ui";

const ui = useUiStore();

const emit = defineEmits<{
  (e: "close"): void;
}>();

const category = ref<"bug" | "idea" | "other">("idea");
const message = ref("");
const contactEmail = ref("");
const destination = ref("");
const submitting = ref(false);
const submitted = ref(false);

async function send(): Promise<void> {
  const text = message.value.trim();
  if (!text) return;
  submitting.value = true;
  try {
    const res = await submitFeedback({
      message: text,
      category: category.value,
      contact_email: contactEmail.value.trim() || null,
    });
    destination.value = res.destination;
    submitted.value = true;
  } catch (exc) {
    ui.toastError("Could not send feedback", exc);
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
    @click.self="emit('close')"
  >
    <div class="w-full max-w-md rounded-lg border border-border bg-card p-5 text-foreground shadow-2xl">
      <div class="mb-3 flex items-center justify-between">
        <h2 class="text-sm font-semibold">Send feedback</h2>
        <button
          type="button"
          class="rounded p-1 text-muted-foreground hover:text-foreground"
          @click="emit('close')"
        >
          ×
        </button>
      </div>

      <div v-if="submitted" class="space-y-3">
        <p class="text-sm">
          Thanks — your message was delivered to
          <span class="font-mono text-xs">{{ destination }}</span>.
        </p>
        <button
          type="button"
          class="w-full rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90"
          @click="emit('close')"
        >
          Close
        </button>
      </div>

      <form v-else class="space-y-3" @submit.prevent="send">
        <p class="text-xs text-muted-foreground">
          Goes directly to <span class="font-mono">nchilaka@digi-setu.com</span> — a real human
          will read it. Not a chatbot, not a ticketing system.
        </p>

        <div>
          <label class="mb-1 block text-[11px] uppercase tracking-wide text-muted-foreground">
            Type
          </label>
          <div class="flex gap-2">
            <button
              v-for="opt in [
                { id: 'bug', label: 'Bug' },
                { id: 'idea', label: 'Idea' },
                { id: 'other', label: 'Other' },
              ]"
              :key="opt.id"
              type="button"
              class="rounded-md border px-2.5 py-1 text-xs"
              :class="category === opt.id
                ? 'border-primary bg-primary/10 text-foreground'
                : 'border-border text-muted-foreground hover:text-foreground'"
              @click="category = opt.id as 'bug' | 'idea' | 'other'"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>

        <div>
          <label class="mb-1 block text-[11px] uppercase tracking-wide text-muted-foreground">
            Message
          </label>
          <textarea
            v-model="message"
            rows="5"
            maxlength="4000"
            placeholder="What's broken or what would you like?"
            class="block w-full resize-y rounded-md border border-border bg-background px-2.5 py-2 text-sm focus:border-ring focus:outline-none"
            required
          />
        </div>

        <div>
          <label class="mb-1 block text-[11px] uppercase tracking-wide text-muted-foreground">
            Reply-to email <span class="text-muted-foreground">(optional)</span>
          </label>
          <input
            v-model="contactEmail"
            type="email"
            maxlength="320"
            placeholder="you@example.com"
            class="block w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-sm focus:border-ring focus:outline-none"
          />
        </div>

        <div class="flex justify-end gap-2 pt-1">
          <button
            type="button"
            class="rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground"
            @click="emit('close')"
          >
            Cancel
          </button>
          <button
            type="submit"
            class="rounded-md bg-primary px-3 py-1.5 text-sm font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-60"
            :disabled="submitting || !message.trim()"
          >
            {{ submitting ? "Sending…" : "Send feedback" }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
