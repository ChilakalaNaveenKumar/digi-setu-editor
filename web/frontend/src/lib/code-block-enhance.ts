/**
 * Post-render enhancer for fenced code blocks.
 *
 * markdown-it produces inert `<pre><code>...</code></pre>` HTML. We can't
 * wire a Vue click handler into that without re-parsing. Instead, after
 * each render we walk the rendered subtree, find every `<pre>` that
 * doesn't yet have a copy button, and append one with a vanilla
 * `addEventListener("click", ...)`. The button reads its sibling
 * `<code>`'s textContent (which is exactly the source the user wants to
 * copy — Shiki's per-token spans contribute zero whitespace pollution).
 *
 * Idempotent: safe to call on every streamed token append. We mark each
 * enhanced `<pre>` with `data-pi-copy="1"` and skip on the next pass.
 *
 * Cleanup is implicit — when Vue unmounts the host element the listener
 * goes with it. We don't need a teardown function.
 */

const MARK_ATTR = "data-pi-copy";

function copyToClipboard(text: string, btn: HTMLButtonElement): void {
  const flash = (label: string) => {
    const prev = btn.textContent;
    btn.textContent = label;
    btn.dataset.flashing = "1";
    setTimeout(() => {
      btn.textContent = prev ?? "Copy";
      delete btn.dataset.flashing;
    }, 1200);
  };

  const fallback = () => {
    // Some embed contexts (file:// previews, sandboxed iframes) block
    // the async clipboard API. The textarea-then-execCommand dance is
    // ugly but still works there. Errors surface as "Copy failed".
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      flash("Copied");
    } catch {
      flash("Failed");
    }
  };

  if (!navigator.clipboard?.writeText) {
    fallback();
    return;
  }
  navigator.clipboard.writeText(text).then(
    () => flash("Copied"),
    () => fallback(),
  );
}

export function enhanceCodeBlocks(host: HTMLElement | null | undefined): void {
  if (!host) return;

  // Cleanup pass: an earlier (pre-fix) version of this enhancer decorated
  // every <pre> in the subtree, including ones inside tool cards. Those
  // stale buttons remain in the DOM because Vue never re-mounted the host.
  // Strip any data-pi-copy="1" pre that is NOT inside .pi-markdown.
  const stale = host.querySelectorAll<HTMLPreElement>(`pre[${MARK_ATTR}="1"]`);
  for (const pre of stale) {
    if (pre.closest(".pi-markdown")) continue;
    pre.removeAttribute(MARK_ATTR);
    pre.querySelectorAll(".pi-copy-btn").forEach((b) => b.remove());
  }

  // Only decorate `<pre>` blocks that live inside markdown-rendered prose
  // (`.pi-markdown`). Tool cards (bash, edit, search_docs, …) render their
  // own `<pre>` for command/output and already ship purpose-built copy
  // controls; if we add another button here it (a) duplicates UX and
  // (b) renders as the literal text "Copy" because the absolute-positioning
  // CSS in app.css is scoped to `.pi-markdown` and never reaches those
  // pre blocks. Result: garbage like "144Copy" trailing every bash output.
  const blocks = host.querySelectorAll<HTMLPreElement>(".pi-markdown pre");
  for (const pre of blocks) {
    if (pre.getAttribute(MARK_ATTR)) continue;
    pre.setAttribute(MARK_ATTR, "1");

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pi-copy-btn";
    btn.textContent = "Copy";
    btn.setAttribute("aria-label", "Copy code to clipboard");
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const code = pre.querySelector("code");
      if (!code) return;
      copyToClipboard(code.textContent ?? "", btn);
    });
    pre.appendChild(btn);
  }
}
