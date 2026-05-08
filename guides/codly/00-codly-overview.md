# Codly — Code Block Enhancements for Typst

> **Codly version:** 1.3.0 (the latest published on the `@preview` registry; `docs.pdf` is titled "1.3.1 manual" but the API is identical — Typst Universe was a release behind at the time the manual was written).
> **Source manual:** `guides/docs.pdf` (the full upstream PDF, 43 pages)
> **Audience:** an LLM agent that authors `.typ` files using the
> [`codly`](https://typst.app/universe/package/codly) package. This sub-tree
> is the Codly reference, organised the same way as the CeTZ reference under
> `../cetz/reference/`.

Codly is a library that **enhances raw code blocks** in Typst. It adds line
numbers, language icons, headers / footers, line skips, line highlights,
column highlights with tags, annotations, references, zebra striping, and
much more — all driven by a single `codly(...)` configuration call (53
named arguments) plus a handful of small helper functions.

## What this folder contains

| Folder | Contents |
| ------ | -------- |
| [`tutorial/`](./tutorial/) | Read-this-first concept material — installation, the `#show: codly-init` idiom, the show-rule-like configuration model, references to lines / highlights / annotations. |
| [`reference/codly/`](./reference/codly/) | The single `codly(...)` configuration entry-point and one page per named argument (53 arguments in total). |
| [`reference/functions/`](./reference/functions/) | Helper functions: `codly-init`, `codly-skip`, `codly-range`, `codly-offset`, `local`, `no-codly`, `yes-codly`, `codly-enable`, `codly-disable`, `codly-reset`. |
| [`reference/icons/`](./reference/icons/) | Built-in language definitions: `typst-icon`, plus a short guide to wiring up Tabler / Font Awesome / Material icon fonts. |

## The 30-second tour

```typst
#import "@preview/codly:1.3.0": *
#show: codly-init

#codly(
  languages: (
    py: (name: "Python", color: green, icon: "🐍"),
  ),
  zebra-fill: aqua.lighten(70%),
)

```py
def fib(n):
    return n if n <= 1 else fib(n - 1) + fib(n - 2)
```
```

Three things to remember:

1. **`#show: codly-init` activates the show rule** for raw blocks.
   Without this line every other Codly call is silently a no-op.
2. **`codly(...)` behaves like a `set` rule, not a `show` rule.** It
   stores configuration in Typst *states*; the configuration applies to
   *every following code block in layout order* until the next `codly(...)`
   or `codly-reset()`. Use [`local(...)`](./reference/functions/05-local.md)
   when you need a one-block override that does not leak.
3. **Most arguments auto-reset after rendering, but some don't** (per-arg
   "Automatically reset" flag in the manual). The reference pages restate
   that flag for every argument so you can predict whether a setting will
   persist.

## How each reference page is structured

Every argument `.md` follows the same shape (mirroring
`../cetz/reference/styling/02-fill.md`):

1. **Summary** — one paragraph, what the argument does.
2. **Card** — type / default / contextual / auto-reset / released-in
   (verbatim from the manual).
3. **Example** — a Typst snippet, plus a link to the runnable file in
   `examples/<NN-name>/`.
4. **Pitfalls / cross-references** — agent-targeted notes (e.g.
   *"requires `display-name: true`"*, *"only used when `lang-format` is
   `auto`"*).

## Quick installation

Codly lives on the Typst package registry (`@preview` namespace), so no
manual install is needed:

```typst
#import "@preview/codly:1.3.0": *
#show: codly-init
```

Once initialised, every raw code block in the document picks up the Codly
formatting. To temporarily turn it off, use
[`no-codly`](./reference/functions/06-no-codly.md) or
[`codly-disable`](./reference/functions/09-codly-disable.md); to bring it
back, use [`yes-codly`](./reference/functions/07-yes-codly.md) or
[`codly-enable`](./reference/functions/08-codly-enable.md).

## Conceptual map (where to start)

| If you want to … | Read |
| ---------------- | ---- |
| Initialise Codly the first time | [`tutorial/01-getting-started.md`](./tutorial/01-getting-started.md) |
| Understand the show-rule-like configuration model | [`reference/codly/00-codly-overview.md`](./reference/codly/00-codly-overview.md) |
| Add line numbers in Roman / circled / custom format | [`reference/codly/31-number-format.md`](./reference/codly/31-number-format.md) |
| Show only some line ranges (`codly-range`, `range`, `ranges`) | [`reference/codly/13-range.md`](./reference/codly/13-range.md), [`reference/functions/03-codly-range.md`](./reference/functions/03-codly-range.md) |
| Display headers / footers above and below blocks | [`reference/codly/03-header.md`](./reference/codly/03-header.md), [`reference/codly/07-footer.md`](./reference/codly/07-footer.md) |
| Highlight specific lines or character ranges | [`reference/codly/42-highlighted-lines.md`](./reference/codly/42-highlighted-lines.md), [`reference/codly/44-highlights.md`](./reference/codly/44-highlights.md) |
| Add side annotations spanning a range of lines | [`reference/codly/40-annotations.md`](./reference/codly/40-annotations.md) |
| Pretty language pills (name + colour + icon) | [`reference/codly/16-languages.md`](./reference/codly/16-languages.md), [`reference/icons/00-icons-overview.md`](./reference/icons/00-icons-overview.md) |
| Reference a line, highlight, or annotation from prose | [`tutorial/02-referencing.md`](./tutorial/02-referencing.md) |
| Override Codly settings for a single block only | [`reference/functions/05-local.md`](./reference/functions/05-local.md) |

## Notes on fidelity

- All argument names, default values, type signatures, "contextual" flags,
  and "automatically reset" flags are taken verbatim from the upstream
  manual (`guides/docs.pdf`, Codly 1.3.1 manual targeting package 1.3.0).
- Where the manual's own example mixed Codly with `@preview/codly-languages`
  (the companion language-definitions package), the example file does
  the same so it compiles with no extra configuration.
- Where the manual references `block.inset`, `block.radius`,
  `grid.cell`, `grid.header`, etc., the cross-references point at the
  Typst standard-library docs.
