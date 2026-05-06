#!/usr/bin/env python3
"""One-shot Vertex/Anthropic call — no tools, raw Messages API.

Compare against the pi/Gemini run at logs/smoke-codly-*.log."""
from __future__ import annotations
import json, os, sys, time, urllib.request, urllib.error, subprocess

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "frontend-472812")

def token() -> str:
    return subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()

def call(region: str, model: str, prompt: str, max_tokens: int = 4096) -> dict:
    host = "aiplatform.googleapis.com" if region == "global" else f"{region}-aiplatform.googleapis.com"
    url = (
        f"https://{host}/v1/projects/{PROJECT}"
        f"/locations/{region}/publishers/anthropic/models/{model}:rawPredict"
    )
    body = {
        "anthropic_version": "vertex-2023-10-16",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token()}",
            "Content-Type": "application/json",
            "x-goog-user-project": PROJECT,
        },
        method="POST",
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"_error": e.read().decode(), "_code": e.code, "_elapsed": time.monotonic() - t0}
    return {**data, "_elapsed": time.monotonic() - t0}

if __name__ == "__main__":
    prompt_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/pi_smoke_prompt.txt"
    region = sys.argv[2] if len(sys.argv) > 2 else "us-east5"
    model  = sys.argv[3] if len(sys.argv) > 3 else "claude-sonnet-4-5"
    prompt = open(prompt_path).read()
    print(f"→ region={region} model={model} prompt_bytes={len(prompt)}", file=sys.stderr)
    r = call(region, model, prompt)
    if "_error" in r:
        print(f"!! HTTP {r['_code']} in {r['_elapsed']:.1f}s", file=sys.stderr)
        print(r["_error"])
        sys.exit(1)
    u = r.get("usage", {})
    print(f"── elapsed: {r['_elapsed']:.1f}s  in={u.get('input_tokens','?')}  out={u.get('output_tokens','?')}  stop={r.get('stop_reason','?')}", file=sys.stderr)
    for block in r.get("content", []):
        if block.get("type") == "text":
            print(block["text"])
