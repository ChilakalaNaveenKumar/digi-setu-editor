//! Sidecar lifecycle — spawn the PyInstaller-frozen FastAPI backend with
//! the right environment, wait for /health to respond, and expose a
//! handle the main module can `.terminate()` on app exit.
//!
//! Layout assumptions (matches `desktop/sidecar/` + `desktop/pi-runtime/`):
//!
//!   <bundle>/Resources/sidecar/dist/pi-typst-sidecar(.exe)
//!       PyInstaller one-file binary built from web/backend/app.py.
//!   <bundle>/Resources/pi-runtime/vendor/node-<platform>/bin/node(.exe)
//!       Bundled Node.js interpreter (no system Node required).
//!   <bundle>/Resources/pi-runtime/vendor/pi/
//!       npm install of pi-coding-agent + its dependencies, also
//!       containing the project's own extensions/typst-tools.ts so pi
//!       loads them out of the resource dir, not the user's folder.
//!
//! In `cargo run` (dev), Tauri sets `tauri::path::resource_dir()` to the
//! source-tree-relative path so the same code paths work without a
//! bundle. The sidecar build step (`sidecar/build_sidecar.sh`) drops the
//! binary into `desktop/sidecar/dist/` and `desktop/pi-runtime/vendor/`
//! is populated by `pi-runtime/fetch-node.sh + install-pi.sh`.
//!
//! On port allocation: we ask the OS for a free TCP port via the
//! `portpicker` crate. Hardcoding 8788 (the prod port) breaks if the
//! user already runs the web backend locally, and shipping a desktop
//! app that crashes whenever 8788 is busy is a non-starter.

use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use tauri::{AppHandle, Emitter, Manager};

/// Window of time the sidecar gets to come up before we give up. Cold
/// PyInstaller boot is ~1–2s on Mac, ~3s on Win — 30s is generous but
/// keeps the user from staring at a hung window forever.
const HEALTH_TIMEOUT: Duration = Duration::from_secs(30);
const HEALTH_POLL_INTERVAL: Duration = Duration::from_millis(250);

/// Cloneable so the watchdog and AppState can share the same child +
/// shutdown state without each side maintaining its own view. Both
/// ``child`` and ``shutdown`` are Arc-wrapped — clones are cheap and
/// every clone observes the same underlying state.
#[derive(Clone)]
pub struct SidecarHandle {
    /// Wrapped in Arc<Mutex> because Tauri's WindowEvent handler runs
    /// on a different thread than the spawn task. We need Send + Sync
    /// to be allowed in `AppState` while still being able to .kill().
    child: Arc<Mutex<Option<Child>>>,
    /// Set true on user/system-initiated termination so the watchdog
    /// stops trying to respawn. Without this the watchdog would treat
    /// our `terminate()` call (e.g. last window closing) as a crash and
    /// fight us by spawning a new sidecar mid-app-shutdown.
    shutdown: Arc<AtomicBool>,
}

impl SidecarHandle {
    /// Best-effort SIGTERM / TerminateProcess. Logs but never panics —
    /// if the child's already gone, fine. Also flips ``shutdown`` so
    /// the watchdog, if still running, stops respawning the child.
    pub fn terminate(&self) {
        // Do this FIRST so the watchdog sees the shutdown flag before
        // it observes the child's exit; otherwise there's a window
        // where the watchdog races us and starts a respawn.
        self.shutdown.store(true, Ordering::SeqCst);
        if let Some(mut child) = self.child.lock().unwrap().take() {
            match child.kill() {
                Ok(_) => log::info!("Sidecar terminate signal sent (pid={})", child.id()),
                Err(err) => log::warn!("Sidecar kill failed (likely already exited): {err}"),
            }
            let _ = child.wait();
        }
    }

    /// True when the user / app shutdown sequence asked us to stop.
    /// Watchdog reads this before each respawn attempt.
    pub fn is_shutting_down(&self) -> bool {
        self.shutdown.load(Ordering::SeqCst)
    }

    /// For ``restart_sidecar`` IPC: take the live child without flipping
    /// the shutdown flag, so the watchdog can respawn after we kill it.
    /// ``terminate()`` is the right call for app-exit (sets shutdown);
    /// this method is the right call for "user asked to recover from
    /// a stuck state, keep the watchdog active".
    pub fn kill_child_for_restart(&self) -> Option<Child> {
        self.child.lock().unwrap().take()
    }
}

#[derive(Debug, thiserror::Error)]
pub enum SidecarError {
    #[error("sidecar binary not found at {0}")]
    BinaryMissing(PathBuf),
    #[error("could not allocate a free local port")]
    NoFreePort,
    #[error("sidecar failed to start: {0}")]
    SpawnFailed(#[from] std::io::Error),
    #[error("sidecar /health did not respond within {timeout:?}")]
    HealthTimeout { timeout: Duration },
    #[error("sidecar exited during startup with status {0:?}")]
    ExitedEarly(Option<i32>),
}

#[derive(Debug)]
struct ResolvedPaths {
    sidecar_bin: PathBuf,
    pi_runtime_root: PathBuf,
    node_bin: PathBuf,
    pi_dir: PathBuf,
    data_root: PathBuf,
}

/// Locate the sidecar + pi runtime resources. In dev (cargo run /
/// tauri dev) the binary lives under the source tree at
/// `<project>/desktop/sidecar/dist/`; in a packaged build it lives under
/// `<bundle>/Contents/Resources/_up_/sidecar/dist/` on Mac (Tauri's
/// `_up_` convention for resources whose path starts with `..`) or
/// `<install>/resources/_up_/sidecar/dist/` on Win.
fn resolve_paths(app: &AppHandle) -> Result<ResolvedPaths, SidecarError> {
    let resource_dir = app
        .path()
        .resource_dir()
        .map_err(|err| SidecarError::SpawnFailed(std::io::Error::other(err.to_string())))?;

    log::debug!("Resource dir: {}", resource_dir.display());

    // The cargo manifest dir (= desktop/src-tauri/) is baked into the
    // binary at compile time. In dev (`cargo run` / `tauri dev`) this
    // gives us a reliable absolute anchor regardless of where the user
    // happens to invoke from. In a production bundle this path won't
    // exist on the user's machine, but resource_dir() above will, so
    // the candidate list below tries both.
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let dev_desktop_root = manifest_dir
        .parent()
        .map(Path::to_path_buf)
        .unwrap_or(manifest_dir.clone());

    // Order matters: in a `cargo tauri build` release the bundled
    // `Resources/sidecar/dist/pi-typst-sidecar` MUST win over the
    // developer's `~/workarea/.../desktop/sidecar/dist/...` even
    // when both exist on the same machine. Otherwise the packaged
    // .app launches with whatever stale dev binary the developer
    // last built, which silently uses the wrong Clerk keys / wrong
    // backend / wrong .env and the user sees a "Lost connection"
    // banner with no obvious cause. We therefore prefer the
    // bundle-relative locations first, and only fall back to the
    // CARGO_MANIFEST_DIR-anchored dev tree (which only resolves on
    // the original build machine) when no bundled binary exists.
    let candidates: Vec<(PathBuf, PathBuf)> = vec![
        // Bundled: Tauri's bundle.resources mapping puts `../sidecar/dist`
        // → `<resource_dir>/sidecar/dist` (and same for pi-runtime).
        (
            resource_dir.join("sidecar").join("dist"),
            resource_dir.join("pi-runtime").join("vendor"),
        ),
        // Older bundle layouts that prefix relative paths with `_up_`.
        (
            resource_dir.join("_up_").join("sidecar").join("dist"),
            resource_dir.join("_up_").join("pi-runtime").join("vendor"),
        ),
        // Dev fallback: anchored on CARGO_MANIFEST_DIR. Only meaningful
        // for `cargo tauri dev` runs straight out of the source tree.
        (
            dev_desktop_root.join("sidecar").join("dist"),
            dev_desktop_root.join("pi-runtime").join("vendor"),
        ),
    ];

    let bin_name = if cfg!(target_os = "windows") {
        "pi-typst-sidecar.exe"
    } else {
        "pi-typst-sidecar"
    };

    for (sidecar_dist, pi_vendor) in &candidates {
        let bin = sidecar_dist.join(bin_name);
        if bin.exists() {
            log::info!("Sidecar binary located: {}", bin.display());
            let (node_bin, pi_dir) = locate_pi_runtime(pi_vendor);
            let data_root = resolve_data_root(app);
            return Ok(ResolvedPaths {
                sidecar_bin: bin,
                pi_runtime_root: pi_vendor.clone(),
                node_bin,
                pi_dir,
                data_root,
            });
        }
    }

    let attempted: Vec<String> = candidates
        .iter()
        .map(|(d, _)| d.join(bin_name).display().to_string())
        .collect();
    log::error!("Sidecar binary missing. Looked in: {attempted:?}");
    Err(SidecarError::BinaryMissing(PathBuf::from(
        attempted.join(", "),
    )))
}

/// Resolve the bundled `node` + `pi` paths. In dev these may not exist
/// yet (the user hasn't run `npm run pi-runtime:fetch`); we still
/// return the expected paths so the sidecar's error message is helpful.
fn locate_pi_runtime(pi_vendor: &Path) -> (PathBuf, PathBuf) {
    let node_subdir = match (std::env::consts::OS, std::env::consts::ARCH) {
        ("macos", "x86_64") => "node-darwin-x64",
        ("macos", "aarch64") => "node-darwin-arm64",
        ("linux", "x86_64") => "node-linux-x64",
        ("linux", "aarch64") => "node-linux-arm64",
        ("windows", _) => "node-win-x64",
        _ => "node-darwin-arm64",
    };

    let node_bin_name = if cfg!(target_os = "windows") {
        "node.exe"
    } else {
        "bin/node"
    };

    let node_bin = pi_vendor.join(node_subdir).join(node_bin_name);
    let pi_dir = pi_vendor.join("pi");
    (node_bin, pi_dir)
}

/// Where the backend keeps its registry/snapshots/chats/audit/
/// shadow-git/everything-else — INCLUDING the bundled pi runtime
/// that the sidecar self-heals on every boot (see
/// `services.pi_integrity` on the Python side).
///
/// Resolution order:
///   1. `DIGI_SETU_HOME` env override (tests, CI, multi-profile).
///   2. Tauri's `app_data_dir()` — the platform-standard app-data
///      location:
///        macOS:   ~/Library/Application Support/com.digi-setu.desktop/
///        Windows: %APPDATA%\Digi Setu\
///        Linux:   ~/.local/share/digi-setu/
///      This is what every other macOS/Windows app does, and (more
///      importantly) it's the only folder that survives an OS upgrade
///      reset / app reinstall on Windows without admin rights. The
///      legacy `~/.digi-setu/` Unix-hidden folder we used to hand out
///      breaks the Windows AppData convention and isn't visible in
///      Finder on Mac without ⌘⇧.
///   3. `~/.digi-setu/` legacy fallback if Tauri's helper fails (only
///      hits in unit-test contexts where there's no real AppHandle).
///
/// Migration: the Python sidecar's `services.pi_integrity` checks
/// for a legacy `~/.digi-setu/` on first boot and `mv`s its contents
/// to the new path so existing chats / login / `.env` carry over
/// without the user noticing. See that module for the full migration
/// rules (idempotent, never overwrites a non-empty target, leaves the
/// legacy dir as an empty marker so we don't re-migrate every boot).
fn resolve_data_root(app: &AppHandle) -> PathBuf {
    if let Some(override_path) = std::env::var_os("DIGI_SETU_HOME") {
        return PathBuf::from(override_path);
    }

    // Tauri's path manager returns the platform-standard app-data
    // dir, derived from the bundle identifier (com.digi-setu.desktop)
    // on macOS and the app product name on Windows / Linux. This is
    // the canonical place for our pi-runtime + chats + workspaces.
    if let Ok(dir) = app.path().app_data_dir() {
        return dir;
    }

    log::warn!(
        "app_data_dir() failed; falling back to legacy ~/.digi-setu/. \
         pi-runtime self-heal still works but Windows users may hit \
         this if %APPDATA% is unset."
    );
    if let Some(home) = home_dir() {
        return home.join(".digi-setu");
    }

    log::warn!("Could not resolve home dir; falling back to /tmp/digi-setu");
    std::env::temp_dir().join("digi-setu")
}

/// Cross-platform home directory lookup. Avoids pulling the `dirs`
/// crate just for one function.
fn home_dir() -> Option<PathBuf> {
    #[cfg(unix)]
    {
        std::env::var_os("HOME").map(PathBuf::from)
    }
    #[cfg(windows)]
    {
        std::env::var_os("USERPROFILE")
            .map(PathBuf::from)
            .or_else(|| std::env::var_os("HOME").map(PathBuf::from))
    }
    #[cfg(not(any(unix, windows)))]
    {
        None
    }
}

/// Kill any orphan `pi-typst-sidecar` processes from prior runs of
/// this app (or prior dev launches). Tauri's single-instance plugin
/// already prevents two GUI processes from running simultaneously,
/// but the *sidecar* can survive the GUI in three real-world cases:
///
///   1. The user force-quits Digi Setu from Activity Monitor /
///      `kill -9` before the GUI can SIGTERM its sidecar.
///   2. The Tauri process itself crashes (segfault, OOM) without
///      running its `Drop` cleanup.
///   3. The user installs a new build over a running app — the new
///      .app launches but the old binary's sidecar is still listening
///      on its loopback port and holding a Clerk session in memory.
///
/// In all three cases the next launch finds zombie sidecars eating
/// ports and (worse) intercepting `127.0.0.1:<random>` traffic the
/// new GUI thinks it's talking to. The user sees "Lost connection
/// to backend" with no obvious cause.
///
/// Fix: at startup, before allocating a fresh port and spawning a
/// new sidecar, sweep the process table for any executable named
/// `pi-typst-sidecar` (including the platform suffix variants) and
/// SIGKILL them. Cheap, idempotent, and matches what every other
/// "single-process" desktop app does (Slack, Discord, VS Code all
/// do this on boot).
///
/// `pub(crate)` so the IPC `restart_and_clean` command in `commands.rs`
/// can call the same sweep when the user clicks the "Restart & Clean
/// Backend" affordance. Centralising the kill-list in one function
/// keeps the boot-time and on-demand paths from drifting.
pub(crate) fn kill_orphan_sidecars() {
    #[cfg(unix)]
    {
        // We previously used `pkill -9 -f pi-typst-sidecar`, but `-f`
        // matches the full command line — which silently kills any
        // unrelated user process whose argv happens to contain that
        // string (e.g. `vim pi-typst-sidecar.log`, `grep pi-typst-…`,
        // a shell history entry replayed via `fc`). Match by
        // executable basename instead so we can never grenade the
        // wrong process. `-x` does an exact comm-name match;
        // pgrep/pkill enforce the 15-char comm limit so the binary
        // name MUST stay short (it's "pi-typst-sidecar" = 16 chars
        // truncated to "pi-typst-sidec" in `comm`, so we match the
        // truncated form too).
        for name in ["pi-typst-sidecar", "pi-typst-sidec"] {
            let _ = std::process::Command::new("pkill")
                .arg("-9")
                .arg("-x")
                .arg(name)
                .status();
        }
    }
    #[cfg(windows)]
    {
        // taskkill /IM already matches by image (executable) name,
        // not arbitrary command-line substring, so this side was
        // already safe.
        let _ = std::process::Command::new("taskkill")
            .arg("/F")
            .arg("/IM")
            .arg("pi-typst-sidecar.exe")
            .arg("/T")
            .status();
    }
}

/// On-disk marker we drop after a successful "version migration" sweep
/// in `<data_root>/.cleanup-version`. Read on every cold start; if its
/// contents differ from the running app's `CARGO_PKG_VERSION` (or the
/// file is missing entirely — first launch on a fresh install) we run
/// the deep-purge path below before the sidecar comes up. After the
/// sweep we write the current version back so the next boot is fast.
const CLEANUP_VERSION_MARKER: &str = ".cleanup-version";

/// Deep state-purge that runs once per app version on cold start.
///
/// `kill_orphan_sidecars()` covers the "previous boot left a sidecar
/// running" case, but it does NOT cover state that survives in the
/// user's data dir between boots and gets stale across upgrades:
///
///   * `<data_root>/tmp/` — short-lived working files the sidecar
///     leaves behind on crash (`.tmp` files, half-written upload
///     chunks). Harmless but gradually eat disk on long-running
///     installs.
///   * `<data_root>/pi-runtime/.lock`-style lock files left behind by
///     a sidecar that died mid-self-heal (see services.pi_integrity).
///     Without removing them the new sidecar sees "another process is
///     still installing pi" and refuses to boot until they age out.
///   * `<data_root>/.session.lock` style transient locks from the
///     previous version's session manager.
///
/// Why version-gated rather than every boot: the deep sweep does
/// filesystem walks (cheap, but non-zero), and a user who relaunches
/// 50 times a day shouldn't pay the cost. A new install or in-place
/// upgrade is the right trigger because:
///   * The Tauri shell binary changed, so any IPC contract drift
///     between versions is most dangerous right here.
///   * Sidecar PyInstaller binary changed, so the in-flight
///     `pi-runtime/` self-heal markers from the OLD sidecar are
///     no-longer-valid signals for the NEW sidecar.
///
/// Idempotent: removing files that don't exist is a no-op. Errors are
/// logged but never panic — the user must always be able to launch
/// the app, even if the data root is read-only or partially corrupt.
fn purge_legacy_state(data_root: &Path) {
    if let Err(err) = std::fs::create_dir_all(data_root) {
        log::warn!(
            "purge_legacy_state: cannot ensure data root {}: {err}",
            data_root.display()
        );
        return;
    }

    let marker_path = data_root.join(CLEANUP_VERSION_MARKER);
    let current_version = env!("CARGO_PKG_VERSION");
    let last_version = std::fs::read_to_string(&marker_path)
        .ok()
        .map(|s| s.trim().to_string())
        .unwrap_or_default();

    if last_version == current_version {
        log::debug!(
            "purge_legacy_state: already cleaned for {current_version}; skipping deep sweep"
        );
        return;
    }

    log::info!(
        "purge_legacy_state: version transition '{}' -> '{}', running deep cleanup",
        if last_version.is_empty() { "<fresh install>" } else { &last_version },
        current_version,
    );

    // 1. Always sweep orphan sidecars, even if a previous deep-purge
    //    on this version succeeded. (We're here because the version
    //    bumped, which means the sidecar binary on disk just got
    //    replaced by the new bundle — kill anything still running
    //    out of the OLD path before we spawn the new one.)
    kill_orphan_sidecars();

    // 2. tmp/ — best-effort recursive remove. We only nuke our own
    //    `tmp` subdir, never the user's wider data root. Anything
    //    truly important (chats, snapshots, registry) lives outside
    //    `tmp/` by convention.
    let tmp_dir = data_root.join("tmp");
    if tmp_dir.exists() {
        match std::fs::remove_dir_all(&tmp_dir) {
            Ok(_) => log::info!(
                "purge_legacy_state: removed {} (was carrying stale work)",
                tmp_dir.display()
            ),
            Err(err) => log::warn!(
                "purge_legacy_state: could not remove {}: {err}",
                tmp_dir.display()
            ),
        }
    }

    // 3. Stale lock / pid files at well-known paths. The list is
    //    deliberately exhaustive — we'd rather over-clean than leave
    //    a stale lock that bricks the next sidecar boot.
    let stale_files = [
        data_root.join("pi-runtime").join(".heal.lock"),
        data_root.join("pi-runtime").join(".install.lock"),
        data_root.join(".session.lock"),
        data_root.join(".registry.lock"),
        data_root.join("tmp.flag"),
    ];
    for path in &stale_files {
        if path.exists() {
            if let Err(err) = std::fs::remove_file(path) {
                log::warn!(
                    "purge_legacy_state: could not remove stale {}: {err}",
                    path.display()
                );
            } else {
                log::info!("purge_legacy_state: removed stale {}", path.display());
            }
        }
    }

    // 4. Drop the new marker so the next boot is fast. We write the
    //    file even if some of the cleanups above failed — the sweep
    //    is best-effort and we don't want a single permission error
    //    to lock us into the slow path forever.
    if let Err(err) = std::fs::write(&marker_path, current_version) {
        log::warn!(
            "purge_legacy_state: could not write marker {}: {err} \
             (next launch will redo the sweep)",
            marker_path.display()
        );
    }
}

pub async fn spawn_sidecar(
    app: &AppHandle,
) -> Result<(SidecarHandle, u16), SidecarError> {
    let paths = resolve_paths(app)?;

    // Versioned deep-purge. Runs the heavy sweep ONLY on the first
    // launch after a fresh install or in-place upgrade; same-version
    // relaunches read the marker file and short-circuit, so this
    // costs ~1ms on the hot path.
    //
    // The deep-purge already kills orphan sidecars internally on the
    // version-mismatch path. We still call ``kill_orphan_sidecars``
    // again below for the SAME-version case (e.g. user force-quit
    // and immediately relaunched) so the boot ALWAYS starts from a
    // clean process table — the user should never have to chase
    // ghost sidecars in Activity Monitor.
    purge_legacy_state(&paths.data_root);

    // Sweep zombie sidecars from prior crashed / force-quit launches
    // BEFORE we pick a port — otherwise a stale sidecar could already
    // be holding the port we'd hand to FastAPI, and the SPA would
    // happily talk to the wrong (stale) process.
    kill_orphan_sidecars();

    // Make sure data root exists before the sidecar tries to write
    // to it. Python's `mkdir(parents=True, exist_ok=True)` would
    // handle this too, but doing it here gives a clearer error if
    // the OS denies us write access.
    if let Err(err) = std::fs::create_dir_all(&paths.data_root) {
        log::warn!(
            "Could not create data root {}: {err}",
            paths.data_root.display()
        );
    }

    let port = portpicker::pick_unused_port().ok_or(SidecarError::NoFreePort)?;
    log::info!("Allocated sidecar port: {port}");

    log::info!(
        "Spawning sidecar:\n  bin       = {}\n  PI_DATA_ROOT = {}\n  pi-runtime  = {}\n  node        = {}\n  pi          = {}",
        paths.sidecar_bin.display(),
        paths.data_root.display(),
        paths.pi_runtime_root.display(),
        paths.node_bin.display(),
        paths.pi_dir.display(),
    );

    let mut cmd = Command::new(&paths.sidecar_bin);
    cmd.arg("--host")
        .arg("127.0.0.1")
        .arg("--port")
        .arg(port.to_string())
        // Let the backend know it's running inside the desktop shell.
        // This is the same flag the existing config.py (line 82) reads.
        .env("PI_MODE", "desktop")
        .env("PI_DATA_ROOT", &paths.data_root)
        // Make sure the Python sidecar's _session_file_path() agrees
        // with the Rust shell's secure_storage::data_root() about
        // where to read/write `.session_id`. Both default to
        // ~/.digi-setu but if the user (or our test rigs) override
        // DIGI_SETU_HOME on the parent process we MUST forward it
        // here — otherwise Rust writes /custom/.session_id and
        // Python reads /home/.digi-setu/.session_id and SSO breaks
        // silently.
        .env("DIGI_SETU_HOME", &paths.data_root)
        // Force subprocess runtime — desktop never uses Docker.
        .env("PI_SESSION_RUNTIME", "subprocess")
        // Tell pi_session.py where the bundled Node + pi live so the
        // FastAPI backend can spawn `pi --mode rpc` without depending
        // on whatever Node the user happens to have on their PATH.
        //
        // These are the BUNDLE paths (read-only, code-signed). The
        // sidecar's ``services.pi_integrity`` boot hook mirrors the
        // bundle vendor dir into ``$DIGI_SETU_HOME/pi-runtime/`` and
        // overrides these env vars to point at the writable user-
        // folder copy before any pi process is spawned. We also pass
        // the bundle vendor dir explicitly so integrity knows where
        // to mirror FROM (the bundle is the source of truth — every
        // app update brings a fresh bundle that supersedes the
        // user-folder copy).
        .env("PI_DESKTOP_NODE_BIN", &paths.node_bin)
        .env("PI_DESKTOP_PI_DIR", &paths.pi_dir)
        .env("PI_DESKTOP_BUNDLE_VENDOR_DIR", &paths.pi_runtime_root)
        // Tells the sidecar's heartbeat module which app version it
        // belongs to. We use the Tauri crate's CARGO_PKG_VERSION
        // (the same value that gates ``purge_legacy_state`` above)
        // so the cloud sees the bundle version, not the Python
        // sidecar's internal __version__ — they're built together
        // but only the bundle version is what users have installed.
        .env("PI_DESKTOP_APP_VERSION", env!("CARGO_PKG_VERSION"))
        // Default the AI's permission posture to the Cursor-style
        // approve-risky mode. The user can toggle it from the UI;
        // this is just the first-launch default.
        // First-launch default: `auto` — prompt for risky tools and
        // auto-approve after 15s if no click. Users can switch to
        // `approve_all` (silent) or `manual` (block until clicked) from
        // the chat settings picker. The picker persists per-user.
        .env("PI_PERMISSION_MODE_DEFAULT", "auto")
        // CORS: in desktop the SPA is served from tauri://localhost
        // (custom protocol). Add it to the allow-list so the FastAPI
        // CORSMiddleware doesn't refuse the SPA's first call.
        .env(
            "PI_CORS_EXTRA_ORIGINS",
            "tauri://localhost,http://tauri.localhost,https://tauri.localhost",
        )
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    // Forward the build-time-baked Clerk + cloud-target env vars to
    // the sidecar. Finder-launched .app processes do NOT inherit the
    // user's shell env, so without this the sidecar would boot with
    // empty Clerk creds and `auth_required = false` — the SPA would
    // hide the sign-in button entirely. See build.rs for how these
    // values get embedded at compile time. We only set the var when
    // it has a non-empty value so the runtime config.py's normal
    // resolution chain (shell-env > .env > unset) is preserved
    // for any key we didn't bake in.
    let baked = [
        ("CLERK_PUBLISHABLE_KEY", env!("DIGI_SETU_CLERK_PUBLISHABLE_KEY")),
        ("CLERK_SECRET_KEY", env!("DIGI_SETU_CLERK_SECRET_KEY")),
        (
            "CLERK_PUBLISHABLE_KEY_PROD",
            env!("DIGI_SETU_CLERK_PUBLISHABLE_KEY_PROD"),
        ),
        (
            "CLERK_SECRET_KEY_PROD",
            env!("DIGI_SETU_CLERK_SECRET_KEY_PROD"),
        ),
        ("PI_CLOUD_API_BASE", env!("DIGI_SETU_PI_CLOUD_API_BASE")),
        ("PI_RELAY_BASE", env!("DIGI_SETU_PI_RELAY_BASE")),
        ("CLERK_TENANT", env!("DIGI_SETU_CLERK_TENANT")),
    ];
    for (key, value) in baked.iter() {
        if !value.is_empty() {
            cmd.env(key, value);
        }
    }

    // On Windows, hide the console window the child would otherwise
    // pop. Without this the user sees a flash of cmd.exe on every
    // app launch.
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }

    let mut child = cmd.spawn()?;
    let pid = child.id();
    log::info!("Sidecar PID: {pid}");

    // Pump stdout/stderr to the host log so users + we can see what
    // the backend is doing. Each line gets a `[sidecar]` prefix.
    if let Some(stdout) = child.stdout.take() {
        std::thread::spawn(move || pump("stdout", stdout));
    }
    if let Some(stderr) = child.stderr.take() {
        std::thread::spawn(move || pump("stderr", stderr));
    }

    let child_arc = Arc::new(Mutex::new(Some(child)));
    let shutdown = Arc::new(AtomicBool::new(false));
    let handle = SidecarHandle {
        child: child_arc.clone(),
        shutdown: shutdown.clone(),
    };

    wait_for_health(port, &child_arc).await?;

    Ok((handle, port))
}

/// Continuous liveness watchdog. Polls the sidecar child every
/// ``WATCHDOG_INTERVAL`` and, if the process exits unexpectedly,
/// respawns it with exponential backoff.
///
/// Why we need this beyond the health-check at startup:
///   * Long-running PyInstaller builds can OOM (especially after a
///     leaky LLM streaming session); macOS will kill us silently.
///   * A panicking import inside the sidecar (corrupted registry.json,
///     missing pi-runtime, broken ~/.digi-setu/.env) takes the
///     process down. Without a watchdog the user has to quit and
///     reopen the .app, AND if they don't know which exact file is
///     poisoned, even relaunching just hangs.
///   * The OS sleep/wake transition can leave the FastAPI uvicorn
///     event loop in a wedged state. We can't detect that here
///     directly, but if the SPA's health watchdog escalates to
///     ``restart_sidecar`` we at least have one place to do the
///     respawn.
///
/// Backoff: ``WATCHDOG_BACKOFF_SCHEDULE`` slots, capped. After the
/// last slot, attempts continue at the cap interval — we never give
/// up entirely, because "give up and tell the user to reinstall"
/// is a worse UX than "keep trying every minute, the user can quit
/// when they're tired of waiting."
///
/// Emits two Tauri events the SPA listens for:
///   * ``backend-restarting``  — sidecar exited; we're attempting to
///                               respawn. Frontend can show a banner.
///   * ``backend-restarted``   — new sidecar is up on the listed port.
///                               Frontend rebinds ``_apiBase`` and
///                               force-reconnects every WS.
const WATCHDOG_INTERVAL: Duration = Duration::from_secs(5);
const WATCHDOG_BACKOFF_SCHEDULE: &[u64] = &[2, 5, 10, 20, 30, 60];

pub fn spawn_watchdog(app: AppHandle, sidecar_handle: SidecarHandle) {
    tauri::async_runtime::spawn(async move {
        watchdog_loop(app, sidecar_handle).await;
    });
}

async fn watchdog_loop(app: AppHandle, handle: SidecarHandle) {
    loop {
        tokio::time::sleep(WATCHDOG_INTERVAL).await;

        // Bail if shutdown started — happens right before .terminate()
        // returns control to the app's WindowEvent handler.
        if handle.is_shutting_down() {
            log::info!("Watchdog: shutdown flag set, exiting");
            return;
        }

        // Snapshot the child's status without holding the lock across
        // the .await below. If it exited, we surface the exit code
        // (useful for debugging crash loops).
        let exit_status = {
            let mut guard = handle.child.lock().unwrap();
            match guard.as_mut() {
                Some(c) => match c.try_wait() {
                    Ok(Some(status)) => Some(status),
                    Ok(None) => continue, // still running
                    Err(err) => {
                        log::warn!("Watchdog: try_wait failed: {err}");
                        continue;
                    }
                },
                None => {
                    // .terminate() took the child but didn't flip the
                    // shutdown flag in time? Defensive — treat as
                    // shutdown and exit.
                    log::warn!("Watchdog: child slot empty without shutdown flag");
                    return;
                }
            }
        };

        let Some(status) = exit_status else { continue };
        log::warn!(
            "Watchdog: sidecar exited with status {:?}; respawning",
            status.code()
        );
        let _ = app.emit("backend-restarting", status.code().unwrap_or(-1));

        // Drop the dead child handle so the next .kill_orphan_sidecars
        // sweep doesn't double-kill it.
        {
            let mut guard = handle.child.lock().unwrap();
            *guard = None;
        }

        // Respawn with backoff. We DON'T re-create the SidecarHandle —
        // the existing one's child slot gets refilled. This way the
        // outer AppState reference (held by `terminate()` on shutdown)
        // still points at the live process.
        let mut attempt: usize = 0;
        loop {
            if handle.is_shutting_down() {
                return;
            }

            match spawn_sidecar(&app).await {
                Ok((new_handle, new_port)) => {
                    log::info!("Watchdog: respawned sidecar on port {new_port}");
                    // Move the new child + shutdown flag into the live
                    // handle. We keep the original `shutdown` Arc so
                    // any outstanding callers of `is_shutting_down`
                    // continue to see the same state.
                    {
                        let mut guard = handle.child.lock().unwrap();
                        *guard = std::mem::replace(
                            &mut *new_handle.child.lock().unwrap(),
                            None,
                        );
                    }

                    // Update AppState.backend_port so future
                    // `get_backend_port` IPC calls return the new port.
                    let state = app.state::<crate::AppState>();
                    *state.backend_port.lock().unwrap() = Some(new_port);

                    let _ = app.emit("backend-restarted", new_port);
                    break;
                }
                Err(err) => {
                    let slot = WATCHDOG_BACKOFF_SCHEDULE
                        .get(attempt)
                        .copied()
                        .unwrap_or(*WATCHDOG_BACKOFF_SCHEDULE.last().unwrap());
                    log::error!(
                        "Watchdog: respawn attempt {attempt} failed: {err} \
                         (next attempt in {slot}s)"
                    );
                    let _ = app.emit("backend-restart-failed", err.to_string());
                    attempt = attempt.saturating_add(1);
                    tokio::time::sleep(Duration::from_secs(slot)).await;
                }
            }
        }
    }
}

fn pump<R: std::io::Read>(stream: &'static str, mut reader: R) {
    use std::io::{BufRead, BufReader};
    let reader = BufReader::new(&mut reader);
    for line in reader.lines().map_while(Result::ok) {
        log::info!("[sidecar:{stream}] {line}");
    }
}

async fn wait_for_health(
    port: u16,
    child: &Arc<Mutex<Option<Child>>>,
) -> Result<(), SidecarError> {
    // /healthz matches the backend route in routes/health.py. We poll
    // it because /api/config does too much (loads Clerk + Stripe state)
    // for a hot-loop probe.
    let url = format!("http://127.0.0.1:{port}/healthz");
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .map_err(|err| SidecarError::SpawnFailed(std::io::Error::other(err.to_string())))?;

    let started = Instant::now();
    while started.elapsed() < HEALTH_TIMEOUT {
        // Bail early if the child died (PyInstaller boot crash, port
        // already taken, missing dep). Without this we'd just sit
        // hammering /health for 30s.
        {
            let mut guard = child.lock().unwrap();
            if let Some(c) = guard.as_mut() {
                if let Ok(Some(status)) = c.try_wait() {
                    return Err(SidecarError::ExitedEarly(status.code()));
                }
            }
        }

        match client.get(&url).send().await {
            Ok(resp) if resp.status().is_success() => return Ok(()),
            _ => tokio::time::sleep(HEALTH_POLL_INTERVAL).await,
        }
    }

    Err(SidecarError::HealthTimeout {
        timeout: HEALTH_TIMEOUT,
    })
}
