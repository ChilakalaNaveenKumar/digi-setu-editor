use std::fs;
use std::path::PathBuf;

fn main() {
    // Bake Clerk + cloud-target env vars into the binary so they're
    // available no matter how the user launches the .app (Finder
    // double-click does NOT inherit the developer's shell env, so a
    // sidecar that read its keys from os.environ at runtime would
    // come up with `auth_required = false` and the SPA would hide
    // the sign-in button).
    //
    // Source of truth: `desktop/backend/.env` on the build machine.
    // We read it at COMPILE time and re-emit each KEY=VAL pair via
    // `cargo:rustc-env=DIGI_SETU_<KEY>=<VAL>` so `env!(...)` /
    // `option_env!(...)` in src/sidecar.rs can pull the strings into
    // the linked binary as `&'static str`. The sidecar is then
    // spawned with those exact values forwarded as real env vars.
    //
    // Variables we care about (all optional — missing ones just
    // fall through to the sidecar's existing `.env` / shell-env
    // resolution path):
    //   CLERK_PUBLISHABLE_KEY        (test tenant)
    //   CLERK_SECRET_KEY             (test tenant)
    //   CLERK_PUBLISHABLE_KEY_PROD   (prod tenant)
    //   CLERK_SECRET_KEY_PROD        (prod tenant)
    //   PI_CLOUD_API_BASE
    //   PI_RELAY_BASE
    //   CLERK_TENANT                 (force tenant override)
    //
    // Trade-off: embedding the Clerk SECRET in the binary is a known
    // smell — anyone who has the .app can `strings` it out. Long-
    // term we'll move every secret-needing call (JWT verification,
    // session refresh) to the cloud backend so the desktop only ever
    // holds the publishable key. For v1 launch, embedding is the
    // pragmatic choice that lets users sign in at all.
    let backend_env_path: PathBuf = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("backend")
        .join(".env");
    println!("cargo:rerun-if-changed={}", backend_env_path.display());
    println!("cargo:rerun-if-env-changed=DIGI_SETU_FORCE_REBUILD");

    let wanted = [
        "CLERK_PUBLISHABLE_KEY",
        "CLERK_SECRET_KEY",
        "CLERK_PUBLISHABLE_KEY_PROD",
        "CLERK_SECRET_KEY_PROD",
        "PI_CLOUD_API_BASE",
        "PI_RELAY_BASE",
        "CLERK_TENANT",
    ];

    // Tell cargo to re-run THIS script if any of the wanted env vars
    // change between runs. Without these declarations cargo fingerprints
    // build.rs based on its source + declared rerun-if hooks only —
    // bumping PI_CLOUD_API_BASE in the shell wouldn't trigger a
    // rebuild and the binary would silently keep the OLD baked value.
    // (We learned this the hard way after a wrong api.digi-setu.com
    // baked into a release survived a fix because `cargo tauri build`
    // didn't think build.rs needed re-running.)
    for k in wanted.iter() {
        println!("cargo:rerun-if-env-changed={}", k);
    }

    // Layer 1: shell env (e.g. CI sets these, or the developer
    // exported them before `cargo tauri build`).
    let mut values: std::collections::HashMap<String, String> =
        std::collections::HashMap::new();
    for k in wanted.iter() {
        if let Ok(v) = std::env::var(k) {
            if !v.is_empty() {
                values.insert((*k).into(), v);
            }
        }
    }

    // Layer 2: desktop/backend/.env (the local-dev source of truth).
    // Shell-env wins over .env — same precedence the sidecar uses
    // at runtime, so the build mirrors runtime semantics.
    if let Ok(contents) = fs::read_to_string(&backend_env_path) {
        for line in contents.lines() {
            let line = line.trim();
            if line.is_empty() || line.starts_with('#') {
                continue;
            }
            let line = line.strip_prefix("export ").unwrap_or(line);
            if let Some((k, v)) = line.split_once('=') {
                let k = k.trim();
                if !wanted.iter().any(|w| *w == k) {
                    continue;
                }
                let v = v.trim();
                let v = v
                    .strip_prefix('"')
                    .and_then(|s| s.strip_suffix('"'))
                    .or_else(|| v.strip_prefix('\'').and_then(|s| s.strip_suffix('\'')))
                    .unwrap_or(v);
                values.entry(k.into()).or_insert_with(|| v.into());
            }
        }
    }

    // ── Live-secret guard ──────────────────────────────────────────
    // Refuse to bake a production Clerk secret key (`sk_live_…`) into
    // the binary unless the operator has explicitly opted in via the
    // `DIGI_SETU_ALLOW_EMBED_LIVE_SECRET=1` env var. Every public
    // download of a build that embeds a live secret is a Clerk
    // takeover risk — `strings <bundle>/Contents/MacOS/digi-setu`
    // will reveal it on any unprotected machine.
    //
    // The opt-in exists so internal/test builds (where the secret
    // isn't actually live, or where the operator has accepted the
    // risk for a controlled distribution list) can still ship.
    // CI / public-release pipelines should never set the flag.
    let allow_live = std::env::var("DIGI_SETU_ALLOW_EMBED_LIVE_SECRET")
        .map(|v| v == "1" || v.eq_ignore_ascii_case("true"))
        .unwrap_or(false);
    println!("cargo:rerun-if-env-changed=DIGI_SETU_ALLOW_EMBED_LIVE_SECRET");

    let secret_keys = ["CLERK_SECRET_KEY", "CLERK_SECRET_KEY_PROD"];
    for k in secret_keys.iter() {
        if let Some(v) = values.get(*k) {
            if v.starts_with("sk_live_") && !allow_live {
                panic!(
                    "\n\n\
                    [build.rs] Refusing to embed a LIVE Clerk secret key ({k}=sk_live_…) \n\
                    into the desktop binary. Anyone with the .app/.exe could extract it \n\
                    via `strings` and impersonate any user.\n\n\
                    Resolve one of:\n\
                      • Move JWT verification + session refresh to the cloud backend so \n\
                        the desktop only needs the publishable key (recommended).\n\
                      • Use a Clerk *test* secret (sk_test_…) for desktop builds and \n\
                        keep prod auth cloud-only.\n\
                      • For an internal/early-access build, set \n\
                        DIGI_SETU_ALLOW_EMBED_LIVE_SECRET=1 to acknowledge the \n\
                        risk and bypass this guard. The CI workflow sets it at \n\
                        env-block scope; do the same locally only when you \n\
                        intentionally want a live-tenant build.\n\n"
                );
            }
        }
    }

    for k in wanted.iter() {
        let v = values.get(*k).cloned().unwrap_or_default();
        // `cargo:rustc-env` injects this as a compile-time env var
        // so `env!("DIGI_SETU_<key>")` can read it. We always emit
        // (empty string when missing) so option_env!() returns
        // Some("") rather than None — simpler downstream branch.
        println!("cargo:rustc-env=DIGI_SETU_{}={}", k, v);
    }

    tauri_build::build()
}
