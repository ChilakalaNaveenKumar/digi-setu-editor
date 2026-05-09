<!--
  Feedback — proper page (not a modal). Same data shape and submit
  pipeline as the old FeedbackModal, just hosted at /feedback so we
  can link from the brand header without stealing focus / scroll
  position.

  Three things the original feedback called out as broken in the
  prior product:
    1. "Why are the Feedback windows slightly angled?" — implied
       something silly was happening. We use a plain page layout.
    2. "It was also not clear who this feedback is sent to" — we
       show the destination email as a literal string at the top, not
       an icon, not a hover tooltip.
    3. "It doesn't even have a page" — fixed: this is a real route.

  Three categories (Bug / Idea / Other) with optional reply-to email
  + 4000-char message. Submitted state shows a confirmation card so
  the user knows the round-trip succeeded.
-->
<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { Icon } from "@iconify/vue";

import BrandHeader from "../components/BrandHeader.vue";
import { submitFeedback } from "../api/feedback";
import { useUiStore } from "../stores/ui";

const router = useRouter();
const ui = useUiStore();

const category = ref<"bug" | "idea" | "other">("idea");
const message = ref("");
const contactEmail = ref("");
const destination = ref("");
const submitting = ref(false);
const submitted = ref(false);

const TYPES: Array<{
  id: "bug" | "idea" | "other";
  label: string;
  icon: string;
  description: string;
}> = [
  { id: "bug", label: "Bug", icon: "codicon:bug", description: "Something broke or behaves unexpectedly." },
  { id: "idea", label: "Idea", icon: "codicon:lightbulb", description: "A feature or change you'd like." },
  { id: "other", label: "Other", icon: "codicon:comment", description: "Question, comment, or anything else." },
];

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

function reset(): void {
  category.value = "idea";
  message.value = "";
  contactEmail.value = "";
  submitted.value = false;
  destination.value = "";
}

function backHome(): void {
  router.push("/");
}
</script>

<template>
  <div class="flex min-h-screen flex-col bg-background text-foreground">
    <!-- BrandHeader hides its own Feedback button on this route since
         we already are on the feedback page; the showFeedback prop
         is left at its default and the link itself simply re-renders
         the same page (no harm). -->
    <BrandHeader
      :links="[
        { to: '/pricing', label: 'Pricing' },
        { to: '/privacy', label: 'Privacy' },
        { to: '/terms', label: 'Terms' },
      ]"
      :show-feedback="false"
    />

    <main class="mx-auto w-full max-w-2xl flex-1 px-6 py-12">
      <header class="mb-8">
        <h1 class="text-h1 font-semibold tracking-tight md:text-h1">
          Send feedback
        </h1>
        <p class="mt-2 text-lead leading-relaxed text-muted-foreground">
          Goes directly to
          <span class="font-mono text-foreground">support@digi-setu.com</span>
          — a real human reads it. No ticketing system, no chatbot.
        </p>
      </header>

      <!-- ── SUCCESS STATE ─────────────────────────────────────────── -->
      <section
        v-if="submitted"
        class="rounded-lg border border-success/30 bg-success/5 p-6"
      >
        <div class="flex items-start gap-3">
          <Icon icon="codicon:check-all" class="mt-0.5 h-5 w-5 shrink-0 text-success" />
          <div class="flex-1">
            <h2 class="text-lead font-semibold text-foreground">
              Thanks — your feedback was delivered.
            </h2>
            <p class="mt-1 text-lead text-muted-foreground">
              Sent to
              <span class="font-mono text-foreground">{{ destination }}</span>.
              We'll reply if you left an email.
            </p>
          </div>
        </div>
        <div class="mt-5 flex flex-wrap gap-2">
          <button
            type="button"
            class="rounded-md bg-primary px-3 py-1.5 text-lead font-semibold text-primary-foreground hover:opacity-90"
            @click="reset"
          >
            Send another
          </button>
          <button
            type="button"
            class="rounded-md border border-border bg-card px-3 py-1.5 text-lead text-muted-foreground hover:border-primary/40 hover:text-foreground"
            @click="backHome"
          >
            Back to home
          </button>
        </div>
      </section>

      <!-- ── FORM ──────────────────────────────────────────────────── -->
      <form v-else class="space-y-6" @submit.prevent="send">
        <fieldset>
          <legend class="mb-3 text-body font-semibold uppercase tracking-wide text-muted-foreground">
            What kind of feedback?
          </legend>
          <div class="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <button
              v-for="opt in TYPES"
              :key="opt.id"
              type="button"
              class="flex flex-col items-start gap-1 rounded-lg border p-3 text-left transition-colors"
              :class="category === opt.id
                ? 'border-primary bg-primary/10'
                : 'border-border bg-card hover:border-primary/40'"
              @click="category = opt.id"
            >
              <div class="flex items-center gap-2">
                <Icon
                  :icon="opt.icon"
                  class="h-4 w-4"
                  :class="category === opt.id ? 'text-primary' : 'text-muted-foreground'"
                />
                <span class="text-lead font-semibold">{{ opt.label }}</span>
              </div>
              <span class="text-caption leading-snug text-muted-foreground">
                {{ opt.description }}
              </span>
            </button>
          </div>
        </fieldset>

        <div>
          <label
            for="feedback-message"
            class="mb-2 block text-body font-semibold uppercase tracking-wide text-muted-foreground"
          >
            Your message
            <span class="ml-1 font-mono text-caption normal-case text-muted-foreground/70">
              {{ message.length }}/4000
            </span>
          </label>
          <textarea
            id="feedback-message"
            v-model="message"
            rows="8"
            maxlength="4000"
            placeholder="What's broken, or what would you like to see? Be as specific as you can — screenshots help."
            class="block w-full resize-y rounded-md border border-border bg-card px-3 py-2.5 text-lead leading-relaxed focus:border-primary/50 focus:outline-none"
            required
          />
        </div>

        <div>
          <label
            for="feedback-email"
            class="mb-2 block text-body font-semibold uppercase tracking-wide text-muted-foreground"
          >
            Reply-to email
            <span class="ml-1 font-normal normal-case text-muted-foreground/70">(optional)</span>
          </label>
          <input
            id="feedback-email"
            v-model="contactEmail"
            type="email"
            maxlength="320"
            placeholder="you@example.com"
            class="block w-full rounded-md border border-border bg-card px-3 py-2 text-lead focus:border-primary/50 focus:outline-none"
          />
          <p class="mt-1 text-caption text-muted-foreground">
            Without this we can't write back, but your message still gets read.
          </p>
        </div>

        <div class="flex items-center justify-end gap-2 pt-2">
          <button
            type="button"
            class="rounded-md px-3 py-2 text-lead text-muted-foreground hover:text-foreground"
            @click="backHome"
          >
            Cancel
          </button>
          <button
            type="submit"
            class="flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-lead font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-60"
            :disabled="submitting || !message.trim()"
          >
            <Icon
              :icon="submitting ? 'codicon:loading' : 'codicon:send'"
              :class="submitting && 'animate-spin'"
              class="h-4 w-4"
            />
            {{ submitting ? "Sending…" : "Send feedback" }}
          </button>
        </div>
      </form>
    </main>

    <footer class="border-t border-border bg-card/40 px-6 py-4 text-center text-caption text-muted-foreground">
      © {{ new Date().getFullYear() }} Digi Setu
    </footer>
  </div>
</template>
