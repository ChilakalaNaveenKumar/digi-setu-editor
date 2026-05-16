<!--
  DesktopMaintenanceSection — bundle of "restart" + "update" controls
  for the chat-settings popover, desktop only.

  Why these live in the gear popover (and not in the brand header):
    The header is loud enough already (workspace name, sign-in chip,
    model picker, gear). Burying maintenance in the gear keeps it
    discoverable but out of the way.

  Two affordances:

    1. Restart & Clean Backend
       Calls the `restart_and_clean` IPC, which sweeps every
       pi-typst-sidecar on the system (orphans included) and lets
       the watchdog respawn. The button is the user-facing version
       of the same sweep that runs on every cold launch (see
       desktop/src-tauri/src/sidecar.rs#kill_orphan_sidecars).

       Useful when:
         - a chat hangs and the WS bridge can't reconnect;
         - the user just edited ~/.digi-setu/.env and wants the
           sidecar to re-read it;
         - "the app feels stuck", as a no-think recovery action.

    2. Check for Updates / Update Now
       Two-state button. Initially "Check for updates" — calls
       `check_for_update`, which pings our manifest at
       digi-setu.com. If a new version is published, the button
       transitions to "Update Now" with the new version label
       and changelog summary. Clicking that streams the bundle,
       verifies its signature, installs in place, and restarts.

       Users never have to download a fresh DMG manually. The whole
       cycle is one click + a progress bar.

  Failure handling: every failure surfaces a toast + leaves the UI
  in a state the user can retry from. We DON'T show modal dialogs
  for these — the user's mid-chat and we don't want to steal focus.
-->
<script setup lang="ts">
import { ref } from "vue";
import { Icon } from "@iconify/vue";

import {
  applyUpdateAndRestart,
  checkForUpdate,
  isDesktop,
  restartAndCleanSidecar,
  type UpdateInfo,
} from "../lib/native-bridge";
import { useUiStore } from "../stores/ui";

const ui = useUiStore();

const restarting = ref(false);
const checking = ref(false);
const updateInfo = ref<UpdateInfo | null>(null);
const lastCheckedAt = ref<Date | null>(null);
// True when the most recent check came back as "already on latest".
// Distinct from "never checked" so the button copy can read
// "You're on the latest" instead of the default "Check for updates".
const upToDate = ref(false);
const installing = ref(false);
const downloadedBytes = ref(0);
const totalBytes = ref<number | null>(null);
const updateError = ref<string | null>(null);

const desktop = isDesktop();

async function doRestartAndClean(): Promise<void> {
  if (restarting.value || !desktop) return;
  restarting.value = true;
  try {
    const ok = await restartAndCleanSidecar();
    if (ok) {
      ui.toast({
        message: "Restarting backend — this takes a few seconds.",
        kind: "info",
      });
    } else {
      ui.toast({ message: "Couldn't restart backend.", kind: "error" });
    }
  } finally {
    // Leave a short visual lock so a frantic double-click doesn't
    // fire two restarts. The watchdog respawn is async so we can't
    // synchronously detect "back up" from here — the rest of the
    // SPA is already wired to listen for `backend-restarted`.
    window.setTimeout(() => {
      restarting.value = false;
    }, 1500);
  }
}

async function doCheckForUpdate(): Promise<void> {
  if (checking.value || !desktop) return;
  checking.value = true;
  updateError.value = null;
  try {
    const info = await checkForUpdate();
    lastCheckedAt.value = new Date();
    if (info) {
      updateInfo.value = info;
      upToDate.value = false;
    } else {
      updateInfo.value = null;
      upToDate.value = true;
    }
  } catch (exc) {
    const msg = exc instanceof Error ? exc.message : String(exc);
    updateError.value = msg;
    ui.toast({ message: `Update check failed: ${msg}`, kind: "error" });
  } finally {
    checking.value = false;
  }
}

async function doInstallUpdate(): Promise<void> {
  if (installing.value || !desktop || !updateInfo.value) return;
  installing.value = true;
  downloadedBytes.value = 0;
  totalBytes.value = null;
  updateError.value = null;
  try {
    await applyUpdateAndRestart((p) => {
      downloadedBytes.value += p.chunkBytes;
      if (p.totalBytes != null) totalBytes.value = p.totalBytes;
    });
    // Unreachable on success — `apply_update_and_restart` reboots
    // the process before this resolves. If we DO get here it means
    // the call succeeded but the restart was suppressed somehow;
    // surface a polite hint and let the user reboot manually.
    ui.toast({
      message: "Update installed. Restart Digi Setu to use the new version.",
      kind: "success",
    });
  } catch (exc) {
    const msg = exc instanceof Error ? exc.message : String(exc);
    updateError.value = msg;
    ui.toast({ message: `Update failed: ${msg}`, kind: "error" });
  } finally {
    installing.value = false;
  }
}

function fmtBytes(n: number): string {
  if (n <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let v = n;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v >= 10 || i === 0 ? Math.round(v) : v.toFixed(1)} ${units[i]}`;
}

defineExpose({
  triggerRestartAndClean: doRestartAndClean,
  triggerCheckForUpdate: doCheckForUpdate,
});
</script>

<template>
  <div v-if="desktop" class="border-b border-border px-3 py-2.5">
    <div class="mb-1.5 flex items-baseline justify-between">
      <span class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
        maintenance
      </span>
    </div>

    <!-- Restart & Clean Backend -->
    <button
      type="button"
      class="flex w-full items-center justify-between rounded border border-border bg-background px-2 py-1.5 text-body hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
      :disabled="restarting"
      @click="doRestartAndClean"
    >
      <span class="flex items-center gap-2">
        <Icon
          v-if="restarting"
          icon="codicon:sync"
          class="h-3.5 w-3.5 animate-spin text-muted-foreground"
        />
        <Icon
          v-else
          icon="codicon:debug-restart"
          class="h-3.5 w-3.5 text-muted-foreground"
        />
        <span>{{ restarting ? "Restarting…" : "Restart & clean backend" }}</span>
      </span>
      <kbd
        v-if="!restarting"
        class="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
      >⌘⇧K</kbd>
    </button>
    <p class="mt-1.5 text-caption leading-tight text-muted-foreground">
      Stops every Digi Setu backend process (including stragglers from
      previous sessions) and starts a fresh one.
    </p>

    <!-- Update -->
    <div class="mt-3 flex flex-col gap-1.5">
      <!-- No info yet OR in the middle of a check -->
      <button
        v-if="!updateInfo"
        type="button"
        class="flex w-full items-center justify-between rounded border border-border bg-background px-2 py-1.5 text-body hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="checking"
        @click="doCheckForUpdate"
      >
        <span class="flex items-center gap-2">
          <Icon
            v-if="checking"
            icon="codicon:sync"
            class="h-3.5 w-3.5 animate-spin text-muted-foreground"
          />
          <Icon
            v-else
            icon="codicon:cloud-download"
            class="h-3.5 w-3.5 text-muted-foreground"
          />
          <span>
            {{ checking
              ? "Checking…"
              : upToDate
                ? "You're on the latest version"
                : "Check for updates" }}
          </span>
        </span>
      </button>

      <!-- Update available — surface version + Update Now CTA -->
      <div
        v-else
        class="rounded border border-amber-500/40 bg-amber-500/5 p-2"
      >
        <div class="flex items-center gap-2">
          <Icon
            icon="codicon:cloud-download"
            class="h-4 w-4 text-amber-300"
          />
          <span class="font-mono text-body text-amber-100">
            Update available · v{{ updateInfo.version }}
          </span>
        </div>
        <p
          v-if="updateInfo.body"
          class="mt-1 max-h-24 overflow-y-auto whitespace-pre-line text-caption leading-tight text-muted-foreground"
        >{{ updateInfo.body }}</p>

        <div v-if="installing" class="mt-2">
          <div class="h-1 overflow-hidden rounded-full bg-muted">
            <div
              class="h-full bg-amber-500/70 transition-[width] duration-100"
              :style="{
                width: totalBytes
                  ? `${Math.min(100, Math.round((downloadedBytes / totalBytes) * 100))}%`
                  : '20%',
              }"
            />
          </div>
          <p class="mt-1 font-mono text-caption text-muted-foreground">
            <span v-if="totalBytes">
              {{ fmtBytes(downloadedBytes) }} of {{ fmtBytes(totalBytes) }}
            </span>
            <span v-else>{{ fmtBytes(downloadedBytes) }} downloaded</span>
          </p>
        </div>

        <button
          v-else
          type="button"
          class="mt-2 w-full rounded bg-amber-500/80 px-2 py-1.5 font-mono text-caption text-amber-50 hover:bg-amber-500"
          @click="doInstallUpdate"
        >
          Update Now &amp; restart
        </button>

        <p class="mt-1.5 text-caption leading-tight text-muted-foreground">
          Digi Setu will close, install the update, and start back up
          where you left off.
        </p>
      </div>

      <p v-if="updateError" class="text-caption leading-tight text-rose-300">
        {{ updateError }}
      </p>
      <p
        v-else-if="lastCheckedAt && !installing"
        class="text-caption leading-tight text-muted-foreground"
      >
        Last checked {{ lastCheckedAt.toLocaleTimeString() }}.
      </p>
    </div>
  </div>
</template>
