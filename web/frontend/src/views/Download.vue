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
import { computed, ref } from "vue";
import { Icon } from "@iconify/vue";


const APP_VERSION = "0.1.0";

const MACOS_ARM_DMG = `Digi-Setu-${APP_VERSION}-arm64.dmg`;
const MACOS_INTEL_DMG = `Digi-Setu-${APP_VERSION}-x64.dmg`;
const LINUX_DEB = `Digi-Setu-${APP_VERSION}-amd64.deb`;
const LINUX_APPIMAGE = `Digi-Setu-${APP_VERSION}-amd64.AppImage`;
const WINDOWS_EXE = `Digi-Setu-${APP_VERSION}-x64-setup.exe`;
const WINDOWS_MSI = `Digi-Setu-${APP_VERSION}-x64.msi`;

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

const primaryHref = computed(() => {
  switch (platform.value) {
    case "mac-arm": return `/downloads/${MACOS_ARM_DMG}`;
    case "mac-intel": return `/downloads/${MACOS_INTEL_DMG}`;
    case "linux-deb": return `/downloads/${LINUX_DEB}`;
    case "linux-appimage": return `/downloads/${LINUX_APPIMAGE}`;
    case "windows": return `/downloads/${WINDOWS_EXE}`;
    default: return `/downloads/${MACOS_ARM_DMG}`;
  }
});

const primaryLabel = computed(() => {
  switch (platform.value) {
    case "mac-arm": return "Download for macOS (Apple Silicon)";
    case "mac-intel": return "Download for macOS (Intel)";
    case "linux-deb": return "Download .deb for Linux";
    case "linux-appimage": return "Download AppImage for Linux";
    case "windows": return "Download for Windows";
    default: return "Download for macOS";
  }
});

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
const macAvailable = true;
// .deb covers Ubuntu/Debian/Mint/Pop!_OS — easily 80%+ of Linux desktop
// installs. .AppImage is held back because Tauri 2's bundler downloads
// its own copy of `linuxdeploy.AppImage` and execs it directly, which
// fails inside our Docker builder (no /dev/fuse). Coming in v0.2 once
// we land a hosted Linux runner with FUSE.
const linuxDebAvailable = true;
const linuxAppImageAvailable = false;
const linuxAvailable = linuxDebAvailable || linuxAppImageAvailable;
const windowsAvailable = false;     // Pending Azure Trusted Signing identity verification
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
        <a
          :href="primaryHref"
          class="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-3 text-base font-semibold text-primary-foreground shadow-sm transition-opacity hover:opacity-90"
        >
          <Icon :icon="primaryIcon" class="h-5 w-5" />
          {{ primaryLabel }}
        </a>
        <p class="text-caption text-muted-foreground">
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
      <div class="overflow-hidden rounded-lg border border-border">
        <!-- macOS Apple Silicon -->
        <component
          :is="macAvailable ? 'a' : 'div'"
          :href="macAvailable ? `/downloads/${MACOS_ARM_DMG}` : undefined"
          class="flex items-center justify-between gap-4 border-b border-border bg-muted/20 px-4 py-3 last:border-b-0"
          :class="macAvailable ? 'hover:bg-muted/40' : 'text-muted-foreground'"
        >
          <div class="flex items-center gap-3">
            <Icon icon="mdi:apple" class="h-5 w-5 text-foreground" />
            <div>
              <div class="font-semibold">macOS · Apple Silicon</div>
              <div class="font-mono text-caption text-muted-foreground">
                {{ macAvailable ? MACOS_ARM_DMG : "Coming soon" }}
              </div>
            </div>
          </div>
          <Icon :icon="macAvailable ? 'mdi:download' : 'mdi:clock-outline'" class="h-5 w-5 text-muted-foreground" />
        </component>

        <!-- macOS Intel -->
        <component
          :is="macAvailable ? 'a' : 'div'"
          :href="macAvailable ? `/downloads/${MACOS_INTEL_DMG}` : undefined"
          class="flex items-center justify-between gap-4 border-b border-border bg-muted/20 px-4 py-3 last:border-b-0"
          :class="macAvailable ? 'hover:bg-muted/40' : 'text-muted-foreground'"
        >
          <div class="flex items-center gap-3">
            <Icon icon="mdi:apple" class="h-5 w-5 text-foreground" />
            <div>
              <div class="font-semibold">macOS · Intel</div>
              <div class="font-mono text-caption text-muted-foreground">
                {{ macAvailable ? MACOS_INTEL_DMG : "Coming soon" }}
              </div>
            </div>
          </div>
          <Icon :icon="macAvailable ? 'mdi:download' : 'mdi:clock-outline'" class="h-5 w-5 text-muted-foreground" />
        </component>

        <!-- Linux .deb -->
        <component
          :is="linuxAvailable ? 'a' : 'div'"
          :href="linuxAvailable ? `/downloads/${LINUX_DEB}` : undefined"
          class="flex items-center justify-between gap-4 border-b border-border bg-muted/20 px-4 py-3 last:border-b-0"
          :class="linuxAvailable ? 'hover:bg-muted/40' : 'text-muted-foreground'"
        >
          <div class="flex items-center gap-3">
            <Icon icon="mdi:linux" class="h-5 w-5 text-foreground" />
            <div>
              <div class="font-semibold">Linux · Debian / Ubuntu (.deb)</div>
              <div class="font-mono text-caption text-muted-foreground">
                {{ linuxDebAvailable ? LINUX_DEB : "Coming soon" }}
              </div>
            </div>
          </div>
          <Icon :icon="linuxDebAvailable ? 'mdi:download' : 'mdi:clock-outline'" class="h-5 w-5 text-muted-foreground" />
        </component>

        <!-- Linux AppImage -->
        <component
          :is="linuxAppImageAvailable ? 'a' : 'div'"
          :href="linuxAppImageAvailable ? `/downloads/${LINUX_APPIMAGE}` : undefined"
          class="flex items-center justify-between gap-4 border-b border-border bg-muted/20 px-4 py-3 last:border-b-0"
          :class="linuxAppImageAvailable ? 'hover:bg-muted/40' : 'text-muted-foreground'"
        >
          <div class="flex items-center gap-3">
            <Icon icon="mdi:linux" class="h-5 w-5 text-foreground" />
            <div>
              <div class="font-semibold">Linux · AppImage (universal)</div>
              <div class="font-mono text-caption text-muted-foreground">
                {{ linuxAppImageAvailable ? LINUX_APPIMAGE : "Coming soon" }}
              </div>
            </div>
          </div>
          <Icon :icon="linuxAppImageAvailable ? 'mdi:download' : 'mdi:clock-outline'" class="h-5 w-5 text-muted-foreground" />
        </component>

        <!-- Windows .exe -->
        <component
          :is="windowsAvailable ? 'a' : 'div'"
          :href="windowsAvailable ? `/downloads/${WINDOWS_EXE}` : undefined"
          class="flex items-center justify-between gap-4 border-b border-border bg-muted/20 px-4 py-3 last:border-b-0"
          :class="windowsAvailable ? 'hover:bg-muted/40' : 'text-muted-foreground'"
        >
          <div class="flex items-center gap-3">
            <Icon icon="mdi:microsoft-windows" class="h-5 w-5 text-foreground" />
            <div>
              <div class="font-semibold">Windows · installer (.exe)</div>
              <div class="font-mono text-caption text-muted-foreground">
                {{ windowsAvailable ? WINDOWS_EXE : "Coming with Trusted Signing approval" }}
              </div>
            </div>
          </div>
          <Icon :icon="windowsAvailable ? 'mdi:download' : 'mdi:clock-outline'" class="h-5 w-5 text-muted-foreground" />
        </component>

        <!-- Windows .msi (IT/MDM) -->
        <component
          :is="windowsAvailable ? 'a' : 'div'"
          :href="windowsAvailable ? `/downloads/${WINDOWS_MSI}` : undefined"
          class="flex items-center justify-between gap-4 bg-muted/10 px-4 py-3"
          :class="windowsAvailable ? 'hover:bg-muted/40' : 'text-muted-foreground'"
        >
          <div class="flex items-center gap-3">
            <Icon icon="mdi:microsoft-windows" class="h-5 w-5" />
            <div>
              <div class="font-semibold">Windows · MSI for IT / MDM</div>
              <div class="font-mono text-caption">
                {{ windowsAvailable ? WINDOWS_MSI : "Coming with Trusted Signing approval" }}
              </div>
            </div>
          </div>
          <Icon :icon="windowsAvailable ? 'mdi:download' : 'mdi:clock-outline'" class="h-5 w-5" />
        </component>
      </div>
    </section>

  </div>
</template>
