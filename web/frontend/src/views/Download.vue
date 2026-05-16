<!--
  Download — public landing page for the desktop installer.

  Linked from BrandHeader's "Get the desktop app" link and any
  marketing surfaces. Stays on the public route table so it loads
  without a Clerk session.

  The .dmg / .deb / .AppImage / .exe artefacts are served by Caddy
  from /srv/pi/downloads on the VM (see deploy/caddy/Caddyfile).
  We hard-code the version + filename here so a release bumps a
  single string and an immutable URL goes live; old links stay
  valid as long as the artefact remains on disk.

  Platform detection notes:
    - macOS Apple Silicon vs Intel: navigator.userAgent doesn't
      reliably differentiate post-Big-Sur (both report "Intel Mac
      OS X 10_15_7"), so we lean on userAgentData.architecture
      where available and fall back to ARM (every Mac sold since
      late 2020 is Apple Silicon).
    - Linux: pick .deb for Debian/Ubuntu/Mint UA hints, otherwise
      .AppImage as the universal fallback.
    - Windows: present the .exe (NSIS) by default; .msi is offered
      under "All downloads" for IT/MDM deploys.

  First-launch UX caveats per platform:
    - macOS: Gatekeeper "unidentified developer" until we finish
      Apple notarisation. Workaround: right-click → Open.
    - Windows: SmartScreen "Unrecognised app" until Azure Trusted
      Signing identity verification finishes. Workaround: More info
      → Run anyway.
    - Linux: AppImage requires `chmod +x`; the .deb is preferred for
      Debian-family distros because dpkg sets the bit for us.
-->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Icon } from "@iconify/vue";
import { useRouter } from "vue-router";

import { apiPost } from "../api/client";
import { useConfigStore } from "../stores/config";

const router = useRouter();
const cfg = useConfigStore();

// Hard-coded fallback used by the SPA when the cloud's
// /api/desktop/latest-version probe fails (offline preview, dev
// without the cloud reachable, or the page rendering before the
// fetch resolves). The cloud-pinned value below shadows this on
// every successful fetch, so a published release bump is live the
// moment the operator runs `set_release_channel(...)` — no SPA
// redeploy required to update the badge / filenames.
const FALLBACK_APP_VERSION = "0.1.0";
const APP_VERSION = ref<string>(FALLBACK_APP_VERSION);

// Auth state. We render the page for everyone (so the URL stays
// shareable in marketing copy and we don't trash SEO), but flip
// the primary CTA to "Sign in to download" when no Clerk session
// exists. This matches the Pricing.vue convention.
const signedIn = ref<boolean | null>(null);
const tracking = ref(false);

onMounted(async () => {
  // 1) Resolve "are we signed in". Same import-pattern as Pricing.vue
  //    so the dev build (cfg.authRequired === false) treats every
  //    visitor as authed.
  if (cfg.authRequired) {
    try {
      const { getToken } = await import("@clerk/vue");
      const t = await getToken();
      signedIn.value = !!t;
    } catch {
      signedIn.value = false;
    }
  } else {
    signedIn.value = true;
  }

  // 2) Pull the canonical latest version. Public endpoint — no auth
  //    needed. Failure leaves the hard-coded fallback in place.
  try {
    const r = await apiPost<{ version: string }>(
      "/api/desktop/latest-version",
      undefined,
    ).catch(async () => {
      // /api/desktop/latest-version is a GET — apiPost will reject
      // with method-not-allowed. Fall back to a plain fetch so the
      // page still resolves a server-side version when present.
      const resp = await fetch("/api/desktop/latest-version", {
        headers: { Accept: "application/json" },
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return await resp.json();
    });
    if (r && typeof r.version === "string" && r.version) {
      APP_VERSION.value = r.version;
    }
  } catch {
    // Network blip or the route hasn't shipped yet — silent fallback.
  }
});

// Filenames are computeds rather than const strings because
// APP_VERSION is now a ref that resolves from the cloud after
// mount. A const interpolation would freeze "Digi-Setu-0.1.0-…"
// at module load and never reflect the live release pointer.
const MACOS_ARM_DMG = computed(() => `Digi-Setu-${APP_VERSION.value}-arm64.dmg`);
const MACOS_INTEL_DMG = computed(() => `Digi-Setu-${APP_VERSION.value}-x86_64.dmg`);
const LINUX_DEB = computed(() => `Digi-Setu-${APP_VERSION.value}-amd64.deb`);
const LINUX_APPIMAGE = computed(() => `Digi-Setu-${APP_VERSION.value}-amd64.AppImage`);
const WINDOWS_EXE = computed(() => `Digi-Setu-${APP_VERSION.value}-x64-setup.exe`);
const WINDOWS_MSI = computed(() => `Digi-Setu-${APP_VERSION.value}-x64.msi`);

type Platform =
  | "mac-arm"
  | "mac-intel"
  | "linux-deb"
  | "linux-appimage"
  | "windows"
  | "other";

const platform = computed<Platform>(() => {
  if (typeof navigator === "undefined") return "other";
  const ua = navigator.userAgent.toLowerCase();
  const platformStr = (navigator.platform || "").toLowerCase();

  // Windows
  if (ua.includes("windows") || platformStr.includes("win")) return "windows";

  // Linux — prefer .deb for Debian-family distros; the UA on most
  // browsers there contains "ubuntu" / "debian" / "mint" hints.
  // We default everyone else to .deb too for now (the AppImage build
  // is on hold — see linuxAppImageAvailable below). Once AppImage
  // ships, swap the fallback back to "linux-appimage".
  if (ua.includes("linux") || platformStr.includes("linux")) {
    return "linux-deb";
  }

  // macOS — try userAgentData.getHighEntropyValues for the real arch
  // when the browser exposes it (Chromium 90+). Otherwise default to
  // ARM since every Mac shipped since late 2020 is Apple Silicon.
  if (ua.includes("mac") || platformStr.includes("mac")) {
    type UAData = { architecture?: string };
    const uad = (navigator as unknown as { userAgentData?: UAData }).userAgentData;
    if (uad?.architecture && uad.architecture.toLowerCase().includes("x86")) {
      return "mac-intel";
    }
    return "mac-arm";
  }

  return "other";
});

// Platform key sent to the cloud's track-download endpoint. Stays
// in sync with the `Platform` type above; the helper exists so
// the click handler doesn't have to duplicate the switch.
const trackingPlatform = computed<string>(() => {
  if (platform.value === "mac-intel" && !macIntelAvailable) {
    // The user is on an Intel Mac but we hand them the arm64 DMG
    // under Rosetta. Telemetry should reflect what they actually
    // clicked, not what we'd ideally hand them.
    return "mac-arm";
  }
  return platform.value;
});

const primaryHref = computed(() => {
  switch (platform.value) {
    case "mac-arm": return `/downloads/${MACOS_ARM_DMG.value}`;
    // No native Intel DMG yet (see `macIntelAvailable` above) — fall
    // back to the arm64 DMG which runs fine under Rosetta 2 on Intel
    // Macs. macOS prompts to install Rosetta on first launch (one-time
    // ~30 sec) and from then on it's transparent.
    case "mac-intel":
      return macIntelAvailable
        ? `/downloads/${MACOS_INTEL_DMG.value}`
        : `/downloads/${MACOS_ARM_DMG.value}`;
    case "linux-deb": return `/downloads/${LINUX_DEB.value}`;
    case "linux-appimage": return `/downloads/${LINUX_APPIMAGE.value}`;
    case "windows": return `/downloads/${WINDOWS_EXE.value}`;
    default: return `/downloads/${MACOS_ARM_DMG.value}`;
  }
});

const primaryLabel = computed(() => {
  // Shadow the platform-specific labels with the auth gate when
  // signed out — the user has to sign in before the bytes fly,
  // and saying so up-front matches Pricing.vue's "Sign in to
  // upgrade" UX.
  if (signedIn.value === false) return "Sign in to download";
  switch (platform.value) {
    case "mac-arm": return "Download for macOS (Apple Silicon)";
    // When we hand an Intel Mac user the arm64 DMG, be explicit about
    // what's happening so they don't think the page is broken when
    // macOS asks them to install Rosetta.
    case "mac-intel":
      return macIntelAvailable
        ? "Download for macOS (Intel)"
        : "Download for macOS (Intel · via Rosetta)";
    case "linux-deb": return "Download .deb for Linux";
    case "linux-appimage": return "Download AppImage for Linux";
    case "windows": return "Download for Windows";
    default: return "Download for macOS";
  }
});

/**
 * Auth-gated download click handler.
 *
 * Behaviour:
 *   - Signed out → redirect to /login with `next=/download`. After
 *     sign-in the user lands back here and clicks again. We don't
 *     auto-trigger the download post-sign-in because Safari + Chrome
 *     suppress programmatic anchor clicks not initiated by a real
 *     user gesture, so a "click happened on a previous page" path
 *     fails silently with no UI feedback.
 *   - Signed in → POST /api/desktop/track-download (records the
 *     event server-side), then synthesise an `<a download>` click
 *     to start the actual download via Caddy's static handler.
 *
 * The synthetic anchor pattern (rather than `window.location.href`)
 * lets the page stay put — important because the download instructions
 * + first-launch warnings are right below the button. Setting
 * window.location would navigate away mid-download.
 */
async function onPrimaryDownload(): Promise<void> {
  if (signedIn.value === false) {
    router.push({ name: "login", query: { next: "/download" } });
    return;
  }
  if (signedIn.value === null || tracking.value) return;
  tracking.value = true;
  try {
    const resp = await apiPost<{
      ok: boolean;
      download_id: number;
      download_url: string;
    }>("/api/desktop/track-download", {
      platform: trackingPlatform.value,
      version: APP_VERSION.value,
    });
    triggerDownload(resp.download_url, primaryHref.value);
  } catch (exc) {
    // If tracking fails (cloud blip, transient 500) we still want
    // the user to be able to install the app — degraded telemetry
    // is preferable to a broken download button. Log + fall through
    // to the static URL so the user gets the bytes either way.
    console.warn("[download] track-download failed; serving anyway", exc);
    triggerDownload(primaryHref.value);
  } finally {
    tracking.value = false;
  }
}

function triggerDownload(url: string, fallback?: string): void {
  const a = document.createElement("a");
  a.href = url || fallback || "";
  // The download attribute hints to the browser "treat as download,
  // not navigation". Caddy also sends Content-Disposition: attachment
  // so this is belt-and-suspenders, but it makes the intent crystal
  // clear inline.
  a.setAttribute("download", "");
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

/**
 * Same auth-gated path as ``onPrimaryDownload``, but for the per-OS
 * rows in the "All downloads" grid below the hero. The grid lets a
 * Linux user on a Mac (or vice versa) override our UA-based platform
 * guess; we want the same auth + tracking story for every code path
 * that hands the user installer bytes.
 */
async function onGridDownload(p: Platform | "windows-msi"): Promise<void> {
  if (signedIn.value === false) {
    router.push({ name: "login", query: { next: "/download" } });
    return;
  }
  if (signedIn.value === null || tracking.value) return;
  const fname = filenameFor(p);
  const fallback = `/downloads/${fname}`;
  tracking.value = true;
  try {
    const resp = await apiPost<{
      ok: boolean;
      download_id: number;
      download_url: string;
    }>("/api/desktop/track-download", {
      platform: p,
      version: APP_VERSION.value,
    });
    triggerDownload(resp.download_url, fallback);
  } catch (exc) {
    console.warn("[download] track-download failed; serving anyway", exc);
    triggerDownload(fallback);
  } finally {
    tracking.value = false;
  }
}

function filenameFor(p: Platform | "windows-msi"): string {
  switch (p) {
    case "mac-arm": return MACOS_ARM_DMG.value;
    case "mac-intel": return MACOS_INTEL_DMG.value;
    case "linux-deb": return LINUX_DEB.value;
    case "linux-appimage": return LINUX_APPIMAGE.value;
    case "windows": return WINDOWS_EXE.value;
    case "windows-msi": return WINDOWS_MSI.value;
    default: return MACOS_ARM_DMG.value;
  }
}

const primaryIcon = computed(() => {
  switch (platform.value) {
    case "windows": return "mdi:microsoft-windows";
    case "linux-deb":
    case "linux-appimage": return "mdi:linux";
    default: return "mdi:apple";
  }
});

const showFirstLaunch = ref(false);

// Platform-specific first-launch instructions. We render the right
// block based on the detected platform; user can still expand it
// manually if their actual OS differs from what we guessed.
const firstLaunchKind = computed<"mac" | "windows" | "linux">(() => {
  if (platform.value === "windows") return "windows";
  if (platform.value === "linux-deb" || platform.value === "linux-appimage") return "linux";
  return "mac";
});

// Status flags per platform — flip these to true the moment the
// matching artefact is uploaded. They control whether a row in the
// "All downloads" grid is a live link or a "Coming soon" placeholder.
//
// macOS Apple Silicon (arm64): produced by GHA's `macos-arm` job
// (.github/workflows/release.yml) on every v*.*.* tag, AND can still
// be built locally with `release.sh --mac` on an M-series Mac.
// macOS Intel (x86_64): currently UNAVAILABLE. The macos-15-intel
// hosted runner's DiskArbitration deadlock kept hanging `create-dmg`
// past our 60-min job budget, so we removed the dedicated job on
// 2026-05-10. Intel Mac users can run the arm64 DMG under Rosetta 2
// in the meantime; when we ship a real Intel installer it'll be a
// universal2 binary from the macos-arm runner (no separate Intel job).
const macArmAvailable = true;
const macIntelAvailable = true;
// .deb covers Ubuntu/Debian/Mint/Pop!_OS — easily 80%+ of Linux desktop
// installs. .AppImage is held back because Tauri 2's bundler downloads
// its own copy of `linuxdeploy.AppImage` and execs it directly, which
// fails inside our Docker builder (no /dev/fuse). Coming in v0.2 once
// we land a hosted Linux runner with FUSE.
const linuxDebAvailable = true;
const linuxAppImageAvailable = false;
// Was previously used to render an "any-flavour Linux" row in the
// All-downloads grid. The grid now branches per-flavour so each row
// reflects its own availability flag, and this aggregate is unused.
// Kept the declaration removed rather than commented to satisfy
// `noUnusedLocals` — the per-flavour flags above carry the truth.
// Windows: produced by GHA's `windows` job (.github/workflows/release.yml).
// Both the .exe (NSIS, end-user-friendly) and the .msi (IT/MDM
// deployment via Group Policy / Intune) come from the same job — flip
// this flag once the artefacts land in /srv/pi/downloads/. Trusted
// Signing is wired up in build-windows.ps1; the page banner above
// already explains the SmartScreen warning users may still see while
// reputation accumulates with Microsoft.
const windowsAvailable = true;
</script>

<template>
  <div class="flex min-h-0 w-full flex-1 flex-col bg-background text-foreground">
    <!-- Hero -->
    <section class="mx-auto max-w-4xl px-6 pt-16 pb-20 text-center">
      <p class="mb-3 inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/40 px-3 py-1 text-caption font-mono uppercase tracking-wide text-muted-foreground">
        <span class="h-1.5 w-1.5 rounded-full bg-emerald-400" />
        v{{ APP_VERSION }} · early access
      </p>
      <h1 class="mt-4 text-4xl font-semibold leading-tight tracking-tight md:text-5xl">
        Digi Setu for desktop
      </h1>
      <p class="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
        Open any folder on your machine, chat with Claude or Gemini about your code,
        and let Digi Setu read, edit, and run things — locally, with your
        own files staying on your machine.
      </p>

      <div class="mt-10 flex flex-col items-center gap-3">
        <!--
          Click rather than direct anchor: signed-out users get
          bounced to /login (and back) before any bytes start;
          signed-in users hit /api/desktop/track-download first
          so the cloud knows who clicked which artefact. The
          static /downloads/* URL is still served by Caddy — we
          only gate the *intent*, not the bytes.
        -->
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-3 text-base font-semibold text-primary-foreground shadow-sm transition-opacity hover:opacity-90 disabled:opacity-60"
          :disabled="tracking || signedIn === null"
          @click="onPrimaryDownload"
        >
          <Icon
            v-if="tracking"
            icon="codicon:sync"
            class="h-5 w-5 animate-spin"
          />
          <Icon
            v-else-if="signedIn === false"
            icon="mdi:lock-outline"
            class="h-5 w-5"
          />
          <Icon v-else :icon="primaryIcon" class="h-5 w-5" />
          {{ primaryLabel }}
        </button>
        <p
          v-if="signedIn === false"
          class="text-caption text-muted-foreground"
        >
          We track downloads against your account so we can tell you
          when an update is ready.
        </p>
        <p v-else class="text-caption text-muted-foreground">
          Free plan included — $10 of cloud credit every month, no card required.
        </p>
        <button
          type="button"
          class="text-caption text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          @click="showFirstLaunch = !showFirstLaunch"
        >
          First launch? Read the one-time install note ↓
        </button>
      </div>
    </section>

    <!-- First-launch: macOS Gatekeeper -->
    <section
      v-if="showFirstLaunch && firstLaunchKind === 'mac'"
      class="mx-auto mb-16 max-w-3xl rounded-lg border border-amber-500/30 bg-amber-500/[0.04] px-6 py-5"
    >
      <div class="flex items-start gap-3">
        <Icon icon="mdi:apple" class="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
        <div class="flex-1 text-body leading-relaxed">
          <h2 class="mb-2 font-semibold text-amber-200">
            macOS · right-click → Open the first time
          </h2>
          <p class="text-foreground/90">
            This early-access build isn't notarised by Apple yet, so the
            first time you double-click the app macOS will say
            <em>"Apple cannot verify Digi Setu is free of malware."</em>
          </p>
          <p class="mt-3 text-foreground/90">
            That's expected. To open it once and trust it forever:
          </p>
          <ol class="mt-2 list-decimal space-y-1.5 pl-5 text-foreground/90">
            <li>Drag <strong>Digi Setu.app</strong> from the .dmg into your <strong>Applications</strong> folder.</li>
            <li>In <strong>Applications</strong>, <strong>right-click</strong> (or Control-click) <strong>Digi Setu.app</strong>.</li>
            <li>Choose <strong>Open</strong> from the menu.</li>
            <li>In the dialog that appears, click <strong>Open</strong> again.</li>
          </ol>
          <p class="mt-3 text-caption text-muted-foreground">
            macOS will remember the choice — every double-click after that
            opens it normally. Apple notarisation is in progress; once it
            lands this step goes away.
          </p>
        </div>
      </div>
    </section>

    <!-- First-launch: Windows SmartScreen -->
    <section
      v-if="showFirstLaunch && firstLaunchKind === 'windows'"
      class="mx-auto mb-16 max-w-3xl rounded-lg border border-amber-500/30 bg-amber-500/[0.04] px-6 py-5"
    >
      <div class="flex items-start gap-3">
        <Icon icon="mdi:microsoft-windows" class="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
        <div class="flex-1 text-body leading-relaxed">
          <h2 class="mb-2 font-semibold text-amber-200">
            Windows · click "More info → Run anyway"
          </h2>
          <p class="text-foreground/90">
            Until our Azure Trusted Signing certificate is issued, Windows
            SmartScreen will warn:
            <em>"Windows protected your PC — Microsoft Defender SmartScreen
            prevented an unrecognised app from starting."</em>
          </p>
          <p class="mt-3 text-foreground/90">To proceed once:</p>
          <ol class="mt-2 list-decimal space-y-1.5 pl-5 text-foreground/90">
            <li>Click <strong>More info</strong> on the SmartScreen dialog.</li>
            <li>Click the <strong>Run anyway</strong> button that appears.</li>
            <li>Walk through the installer (Next → Next → Install).</li>
            <li>Launch <strong>Digi Setu</strong> from the Start menu.</li>
          </ol>
          <p class="mt-3 text-caption text-muted-foreground">
            Identity verification is in progress with Microsoft Trusted
            Signing. Once approved, every fresh installer is signed by
            "Digi Setu" and the SmartScreen warning disappears.
          </p>
        </div>
      </div>
    </section>

    <!-- First-launch: Linux -->
    <section
      v-if="showFirstLaunch && firstLaunchKind === 'linux'"
      class="mx-auto mb-16 max-w-3xl rounded-lg border border-amber-500/30 bg-amber-500/[0.04] px-6 py-5"
    >
      <div class="flex items-start gap-3">
        <Icon icon="mdi:linux" class="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
        <div class="flex-1 text-body leading-relaxed">
          <h2 class="mb-2 font-semibold text-amber-200">
            Linux · install with your package manager
          </h2>
          <p class="text-foreground/90">
            We ship two flavours — pick whichever matches your distro:
          </p>
          <div class="mt-3 space-y-3 text-foreground/90">
            <div>
              <strong>.deb (Debian / Ubuntu / Mint):</strong>
              <pre class="mt-1 overflow-x-auto rounded bg-muted/40 px-3 py-2 font-mono text-caption">sudo apt install ./{{ LINUX_DEB }}</pre>
            </div>
            <div>
              <strong>.AppImage (everything else):</strong>
              <pre class="mt-1 overflow-x-auto rounded bg-muted/40 px-3 py-2 font-mono text-caption">chmod +x {{ LINUX_APPIMAGE }}
./{{ LINUX_APPIMAGE }}</pre>
            </div>
          </div>
          <p class="mt-3 text-caption text-muted-foreground">
            Both bundle GTK 3 + WebKit2GTK 4.1; if your system is older
            than Ubuntu 22.04 you may need to install
            <span class="font-mono">libwebkit2gtk-4.1-0</span> first.
          </p>
        </div>
      </div>
    </section>

    <!-- Feature strip -->
    <section class="mx-auto mb-16 max-w-5xl px-6">
      <div class="grid gap-6 md:grid-cols-3">
        <div class="rounded-lg border border-border bg-muted/20 p-5">
          <Icon icon="mdi:folder-open-outline" class="mb-3 h-6 w-6 text-primary" />
          <h3 class="mb-1 font-semibold">Open any folder</h3>
          <p class="text-caption text-muted-foreground leading-relaxed">
            Your code stays on your machine. Workspaces are saved under
            <span class="font-mono">~/.digi-setu</span> — back it up, sync it, delete it any time.
          </p>
        </div>
        <div class="rounded-lg border border-border bg-muted/20 p-5">
          <Icon icon="mdi:robot-outline" class="mb-3 h-6 w-6 text-primary" />
          <h3 class="mb-1 font-semibold">Claude + Gemini, your pick</h3>
          <p class="text-caption text-muted-foreground leading-relaxed">
            Routes through our cloud subscription by default, or
            bring your own API key (Anthropic / Google / OpenAI) and pay
            your provider direct.
          </p>
        </div>
        <div class="rounded-lg border border-border bg-muted/20 p-5">
          <Icon icon="mdi:shield-key-outline" class="mb-3 h-6 w-6 text-primary" />
          <h3 class="mb-1 font-semibold">Sign in once, stay in</h3>
          <p class="text-caption text-muted-foreground leading-relaxed">
            Cursor-style SSO — your session is stored in the OS keychain
            and silently re-minted in the background. No daily re-logins.
          </p>
        </div>
      </div>
    </section>

    <!-- All downloads grid -->
    <section class="mx-auto mb-20 max-w-3xl px-6">
      <h2 class="mb-4 text-caption font-mono uppercase tracking-wide text-muted-foreground">
        All downloads
      </h2>
      <p
        v-if="signedIn === false"
        class="mb-3 text-caption text-muted-foreground"
      >
        <Icon icon="mdi:lock-outline" class="-mt-0.5 inline h-3.5 w-3.5" />
        Sign in to download — we keep a list of which build you have so
        we can tell you when an update is ready.
      </p>
      <div class="overflow-hidden rounded-lg border border-border">
        <!-- macOS Apple Silicon -->
        <button
          v-if="macArmAvailable"
          type="button"
          class="flex w-full items-center justify-between gap-4 border-b border-border bg-muted/20 px-4 py-3 text-left last:border-b-0 hover:bg-muted/40 disabled:opacity-60"
          :disabled="tracking || signedIn === null"
          @click="onGridDownload('mac-arm')"
        >
          <div class="flex items-center gap-3">
            <Icon icon="mdi:apple" class="h-5 w-5 text-foreground" />
            <div>
              <div class="font-semibold">macOS · Apple Silicon</div>
              <div class="font-mono text-caption text-muted-foreground">
                {{ MACOS_ARM_DMG }}
              </div>
            </div>
          </div>
          <Icon
            :icon="signedIn === false ? 'mdi:lock-outline' : 'mdi:download'"
            class="h-5 w-5 text-muted-foreground"
          />
        </button>
        <div
          v-else
          class="flex items-center justify-between gap-4 border-b border-border bg-muted/20 px-4 py-3 text-muted-foreground last:border-b-0"
        >
          <div class="flex items-center gap-3">
            <Icon icon="mdi:apple" class="h-5 w-5 text-foreground" />
            <div>
              <div class="font-semibold">macOS · Apple Silicon</div>
              <div class="font-mono text-caption">Coming soon</div>
            </div>
          </div>
          <Icon icon="mdi:clock-outline" class="h-5 w-5" />
        </div>

        <!-- macOS Intel -->
        <button
          v-if="macIntelAvailable"
          type="button"
          class="flex w-full items-center justify-between gap-4 border-b border-border bg-muted/20 px-4 py-3 text-left last:border-b-0 hover:bg-muted/40 disabled:opacity-60"
          :disabled="tracking || signedIn === null"
          @click="onGridDownload('mac-intel')"
        >
          <div class="flex items-center gap-3">
            <Icon icon="mdi:apple" class="h-5 w-5 text-foreground" />
            <div>
              <div class="font-semibold">macOS · Intel</div>
              <div class="font-mono text-caption text-muted-foreground">
                {{ MACOS_INTEL_DMG }}
              </div>
            </div>
          </div>
          <Icon
            :icon="signedIn === false ? 'mdi:lock-outline' : 'mdi:download'"
            class="h-5 w-5 text-muted-foreground"
          />
        </button>
        <div
          v-else
          class="flex items-center justify-between gap-4 border-b border-border bg-muted/20 px-4 py-3 text-muted-foreground last:border-b-0"
        >
          <div class="flex items-center gap-3">
            <Icon icon="mdi:apple" class="h-5 w-5 text-foreground" />
            <div>
              <div class="font-semibold">macOS · Intel</div>
              <div class="font-mono text-caption">
                Coming soon — use Apple Silicon DMG via Rosetta meanwhile
              </div>
            </div>
          </div>
          <Icon icon="mdi:clock-outline" class="h-5 w-5" />
        </div>

        <!-- Linux .deb -->
        <button
          v-if="linuxDebAvailable"
          type="button"
          class="flex w-full items-center justify-between gap-4 border-b border-border bg-muted/20 px-4 py-3 text-left last:border-b-0 hover:bg-muted/40 disabled:opacity-60"
          :disabled="tracking || signedIn === null"
          @click="onGridDownload('linux-deb')"
        >
          <div class="flex items-center gap-3">
            <Icon icon="mdi:linux" class="h-5 w-5 text-foreground" />
            <div>
              <div class="font-semibold">Linux · Debian / Ubuntu (.deb)</div>
              <div class="font-mono text-caption text-muted-foreground">
                {{ LINUX_DEB }}
              </div>
            </div>
          </div>
          <Icon
            :icon="signedIn === false ? 'mdi:lock-outline' : 'mdi:download'"
            class="h-5 w-5 text-muted-foreground"
          />
        </button>
        <div
          v-else
          class="flex items-center justify-between gap-4 border-b border-border bg-muted/20 px-4 py-3 text-muted-foreground last:border-b-0"
        >
          <div class="flex items-center gap-3">
            <Icon icon="mdi:linux" class="h-5 w-5 text-foreground" />
            <div>
              <div class="font-semibold">Linux · Debian / Ubuntu (.deb)</div>
              <div class="font-mono text-caption">Coming soon</div>
            </div>
          </div>
          <Icon icon="mdi:clock-outline" class="h-5 w-5" />
        </div>

        <!-- Linux AppImage -->
        <button
          v-if="linuxAppImageAvailable"
          type="button"
          class="flex w-full items-center justify-between gap-4 border-b border-border bg-muted/20 px-4 py-3 text-left last:border-b-0 hover:bg-muted/40 disabled:opacity-60"
          :disabled="tracking || signedIn === null"
          @click="onGridDownload('linux-appimage')"
        >
          <div class="flex items-center gap-3">
            <Icon icon="mdi:linux" class="h-5 w-5 text-foreground" />
            <div>
              <div class="font-semibold">Linux · AppImage (universal)</div>
              <div class="font-mono text-caption text-muted-foreground">
                {{ LINUX_APPIMAGE }}
              </div>
            </div>
          </div>
          <Icon
            :icon="signedIn === false ? 'mdi:lock-outline' : 'mdi:download'"
            class="h-5 w-5 text-muted-foreground"
          />
        </button>
        <div
          v-else
          class="flex items-center justify-between gap-4 border-b border-border bg-muted/20 px-4 py-3 text-muted-foreground last:border-b-0"
        >
          <div class="flex items-center gap-3">
            <Icon icon="mdi:linux" class="h-5 w-5 text-foreground" />
            <div>
              <div class="font-semibold">Linux · AppImage (universal)</div>
              <div class="font-mono text-caption">Coming soon</div>
            </div>
          </div>
          <Icon icon="mdi:clock-outline" class="h-5 w-5" />
        </div>

        <!-- Windows .exe -->
        <button
          v-if="windowsAvailable"
          type="button"
          class="flex w-full items-center justify-between gap-4 border-b border-border bg-muted/20 px-4 py-3 text-left last:border-b-0 hover:bg-muted/40 disabled:opacity-60"
          :disabled="tracking || signedIn === null"
          @click="onGridDownload('windows')"
        >
          <div class="flex items-center gap-3">
            <Icon icon="mdi:microsoft-windows" class="h-5 w-5 text-foreground" />
            <div>
              <div class="font-semibold">Windows · installer (.exe)</div>
              <div class="font-mono text-caption text-muted-foreground">
                {{ WINDOWS_EXE }}
              </div>
            </div>
          </div>
          <Icon
            :icon="signedIn === false ? 'mdi:lock-outline' : 'mdi:download'"
            class="h-5 w-5 text-muted-foreground"
          />
        </button>
        <div
          v-else
          class="flex items-center justify-between gap-4 border-b border-border bg-muted/20 px-4 py-3 text-muted-foreground last:border-b-0"
        >
          <div class="flex items-center gap-3">
            <Icon icon="mdi:microsoft-windows" class="h-5 w-5 text-foreground" />
            <div>
              <div class="font-semibold">Windows · installer (.exe)</div>
              <div class="font-mono text-caption">
                Coming with Trusted Signing approval
              </div>
            </div>
          </div>
          <Icon icon="mdi:clock-outline" class="h-5 w-5" />
        </div>

        <!-- Windows .msi (IT/MDM) -->
        <button
          v-if="windowsAvailable"
          type="button"
          class="flex w-full items-center justify-between gap-4 bg-muted/10 px-4 py-3 text-left hover:bg-muted/40 disabled:opacity-60"
          :disabled="tracking || signedIn === null"
          @click="onGridDownload('windows-msi')"
        >
          <div class="flex items-center gap-3">
            <Icon icon="mdi:microsoft-windows" class="h-5 w-5" />
            <div>
              <div class="font-semibold">Windows · MSI for IT / MDM</div>
              <div class="font-mono text-caption">
                {{ WINDOWS_MSI }}
              </div>
            </div>
          </div>
          <Icon
            :icon="signedIn === false ? 'mdi:lock-outline' : 'mdi:download'"
            class="h-5 w-5"
          />
        </button>
        <div
          v-else
          class="flex items-center justify-between gap-4 bg-muted/10 px-4 py-3 text-muted-foreground"
        >
          <div class="flex items-center gap-3">
            <Icon icon="mdi:microsoft-windows" class="h-5 w-5" />
            <div>
              <div class="font-semibold">Windows · MSI for IT / MDM</div>
              <div class="font-mono text-caption">
                Coming with Trusted Signing approval
              </div>
            </div>
          </div>
          <Icon icon="mdi:clock-outline" class="h-5 w-5" />
        </div>
      </div>
    </section>

  </div>
</template>
