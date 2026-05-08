# `target` — current export format (experimental)

> **Experimental — gated behind `--features html`.**
> The function exists but every call errors with `unknown variable: target` unless you compile with:
>
> ```bash
> typst compile --features html file.typ
> ```
>
> The API design is not yet final. Expect breaking changes.

`target() -> str` is a **contextual** function (must be inside a `context { ... }` block) that returns the current export format:

| Returns      | When                                                     |
| ------------ | -------------------------------------------------------- |
| `"paged"`    | Exporting to PDF, PNG, or SVG                            |
| `"html"`     | Exporting to HTML                                        |
| `"paged"`    | **Inside `html.frame`**, even when the top-level export is HTML |

Use it in **templates and show rules** to author one source of truth that renders sensibly on both paged and HTML targets.

## Canonical pattern: a target-aware element

```typst
#let kbd(it) = context {
  if target() == "html" {
    html.elem("kbd", it)
  } else {
    box(
      fill: rgb("#f6f8fa"),
      stroke: rgb("#d1d9e0b3"),
      inset: (x: 3pt),
      outset: (y: 3pt),
      radius: 3pt,
      raw(it),
    )
  }
}

Press #kbd("F1") for help.
```

Compiled to PDF → boxed pseudo-keycap. Compiled to HTML → `<kbd>F1</kbd>` (inheriting browser styling).

## Pitfalls

- **`unknown variable: target`** — you forgot `--features html`. Add the flag or remove the `target()` call.
- **Bare `target()` outside `context`** errors with the standard "contextual function" message. Wrap with `context { ... }`.
- **Don't bake `target()` into raw content.** Confine it to template-level / show-rule code so the *content* of the document is target-agnostic.
- **`html.frame` flips the target back to `"paged"`** so embedded paged blocks (figures, equations) inside HTML output still hit the paged branch. This is intentional — it lets you nest paged content cleanly.
- **HTML export itself is experimental** in 0.14. Element coverage is incomplete; expect rough edges.

## Examples (compile-verified)

- `examples/28-target/01-target-branching.typ` — `kbd(...)` helper that switches between `html.elem` and a styled `box` based on `target()`. Compile with `typst compile --features html`.

## Reference

- Official: https://typst.app/docs/reference/foundations/target/
- HTML export: https://typst.app/docs/reference/html/
- `html.frame`: https://typst.app/docs/reference/html/frame/
- `context`: https://typst.app/docs/reference/context/
