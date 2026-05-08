# 01 — Getting Started

> **Codly version:** 1.3.0 · **Source:** `docs.pdf` §1–§2

Codly is invoked from any Typst document by importing the package, applying
its show rule, and (optionally) configuring it with the `codly(...)`
function. This page walks through the absolute minimum.

## Hello, Codly

```typst
#import "@preview/codly:1.3.0": *
#show: codly-init

```py
def hello():
    print("Hello, Codly!")
```
```

That's it — every `raw(block: true)` element in the document now picks up
the Codly look (line numbers in the gutter, language pill in the
top-right corner, default rounded corners + thin grey stroke + zebra
stripes).

## The `codly(...)` configuration call

`codly(...)` works **like a `set` rule**, not a `show` rule: it stores
configuration into Typst *states*, and the configuration applies to every
*following* code block in layout order until you call `codly(...)` again
(or `codly-reset()`).

```typst
#codly(
  zebra-fill: aqua.lighten(70%),
  number-format: numbering.with("I"),
)

```py
print("First block uses Roman numerals + aqua zebra")
```

```py
print("So does this one — the codly call is sticky.")
```

#codly-reset()

```py
print("Back to the defaults.")
```
```

The "info card" the manual prints at the top of every argument has five
fields — re-shown on every reference page in this folder:

| Field | Meaning |
| ----- | ------- |
| **Type** | Accepted Typst types (`bool`, `length`, `dictionary`, `function`, …). |
| **Default value** | What you get if you don't set the argument. |
| **Contextual function** | Whether the value can be a `(args) => ...` callback that runs inside a `context { ... }` block. |
| **Automatically reset** | Whether the setting reverts to its default *after each code block* (most cosmetic settings stay sticky; `header` / `footer` / range / annotations etc. reset). |
| **Already released in 1.3.1** | Whether the feature ships in the current release (a few are pre-announcements for the next version). |

## When you want a one-block override: `local(...)`

```typst
#codly(fill: red)

```typ
*Red block*
```

#local(fill: gray, ```typ
*Gray block (this one only)*
```)

```typ
*Red block again — local() did not leak.*
```
```

`local(...)` is the right tool when:

- You want one block (or one section) styled differently without leaking
  the change to the rest of the document.
- You want to attach a per-language style with `show raw.where(lang:
  "rust"): local.with(...)`.

See [`../reference/functions/05-local.md`](../reference/functions/05-local.md)
for the full story (including the `nested:` argument).

## Two warnings from the manual

> Unlike regular set-rules in native Typst, there are two considerations:
>
> - The codly function uses **states** to store the configuration, this
>   means that it is dependent on layout order for the order in which
>   settings are applied.
> - The codly function is **not local**, it sets the configuration for all
>   code blocks that follow it in layout order, unless overriden by another
>   codly call. This means that you cannot use it to set the configuration
>   for a specific code block. To perform this, use the `local` function to
>   set the configuration for a specific "section".

## Disabling and re-enabling

| Goal | Function | Notes |
| ---- | -------- | ----- |
| Globally turn Codly off | `#codly-disable()` | Equivalent to `#codly(enabled: false)`. |
| Globally turn it back on | `#codly-enable()` | Equivalent to `#codly(enabled: true)`. |
| Just one block / section | `#no-codly[ ... ]` | `local(enabled: false, body)`. |
| Just one block / section | `#yes-codly[ ... ]` | `local(enabled: true, body)`. |
| Wipe all customisations back to defaults | `#codly-reset()` | Equivalent to a fresh `codly()` call with no args. |

## Convention used in the rest of this folder

From here on, **only the body of each example is shown** in inline
snippets. Assume the same outer wrapper:

```typst
#import "@preview/codly:1.3.0": *
#show: codly-init

// <snippet here>
```

Each `examples/<n>/<n>.typ` file in the reference folders is the *full,
compilable* version with the wrapper restored.

## Next steps

- [`02-referencing.md`](./02-referencing.md) — referencing lines,
  highlights, and annotations from prose.
- [`../reference/codly/00-codly-overview.md`](../reference/codly/00-codly-overview.md) —
  the full list of 53 arguments grouped by theme.
- [`../reference/functions/00-functions-overview.md`](../reference/functions/00-functions-overview.md) —
  the helper-function family.
