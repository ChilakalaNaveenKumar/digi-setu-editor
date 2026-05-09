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
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use tauri::{AppHandle, Manager};

/// Window of time the sidecar gets to come up before we give up. Cold
/// PyInstaller boot is ~1–2s on Mac, ~3s on Win — 30s is generous but
/// keeps the user from staring at a hung window forever.
const HEALTH_TIMEOUT: Duration = Duration::from_secs(30);
const HEALTH_POLL_INTERVAL: Duration = Duration::from_millis(250);

pub struct SidecarHandle {
    /// Wrapped in Arc<Mutex> because Tauri's WindowEvent handler runs
    /// on a different thread than the spawn task. We need Send + Sync
    /// to be allowed in `AppState` while still being able to .kill().
    child: Arc<Mutex<Option<Child>>>,
}

impl SidecarHandle {
    /// Best-effort SIGTERM / TerminateProcess. Logs but never panics —
    /// if the child's already gone, fine.
    pub fn terminate(&self) {
        if let Some(mut child) = self.child.lock().unwrap().take() {
            match child.kill() {
                Ok(_) => log::info!("Sidecar terminate signal sent (pid={})", child.id()),
                Err(err) => log::warn!("Sidecar kill failed (likely already exited): {err}"),
            }
            let _ = child.wait();
        }
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

/// Where the backend should keep its registry/snapshots/chats/audit/
/// shadow-git/everything-else.
///
/// Per product decision we put EVERYTHING under `~/.digi-setu/` (or
/// `%USERPROFILE%\.digi-setu\` on Windows) — chats, workspaces,
/// audits, snapshots, *and* the user-editable `.env`. One folder the
/// user can `cd ~/.digi-setu`, back up, sync, or wipe.
///
/// Rationale (vs. the OS app-data dir Tauri normally hands out):
///   - User-discoverable. `~/Library/Application Support/...` is
///     hidden in Finder by default; people lose their data.
///   - Single source of truth for "your Digi Setu state". Backups,
///     migration to a new machine, "rm everything and start over"
///     all become a one-line operation.
///   - Mirrors how Claude Code, Aider, fish, ssh, gnupg, npm, gh,
///     etc. all use `~/.<tool>/`. Familiar shape.
///
/// Override with `DIGI_SETU_HOME` env var if you ever need to point
/// elsewhere (handy for tests / CI / multiple-profile setups).
fn resolve_data_root(_app: &AppHandle) -> PathBuf {
    if let Some(override_path) = std::env::var_os("DIGI_SETU_HOME") {
        return PathBuf::from(override_path);
    }

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
fn kill_orphan_sidecars() {
    #[cfg(unix)]
    {
        // pgrep + kill -9 by name. We deliberately do NOT match the
        // full path so this also clears dev-tree sidecars left over
        // from `cargo tauri dev` runs on the developer's machine —
        // they would otherwise outlive the dev process and confuse a
        // subsequent packaged-app launch.
        let _ = std::process::Command::new("pkill")
            .arg("-9")
            .arg("-f")
            .arg("pi-typst-sidecar")
            .status();
    }
    #[cfg(windows)]
    {
        let _ = std::process::Command::new("taskkill")
            .arg("/F")
            .arg("/IM")
            .arg("pi-typst-sidecar.exe")
            .arg("/T")
            .status();
    }
}

pub async fn spawn_sidecar(
    app: &AppHandle,
) -> Result<(SidecarHandle, u16), SidecarError> {
    let paths = resolve_paths(app)?;

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
        .env("PI_DESKTOP_NODE_BIN", &paths.node_bin)
        .env("PI_DESKTOP_PI_DIR", &paths.pi_dir)
        // Default the AI's permission posture to the Cursor-style
        // approve-risky mode. The user can toggle it from the UI;
        // this is just the first-launch default.
        .env("PI_PERMISSION_MODE_DEFAULT", "approve_risky")
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
    let handle = SidecarHandle {
        child: child_arc.clone(),
    };

    wait_for_health(port, &child_arc).await?;

    Ok((handle, port))
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
