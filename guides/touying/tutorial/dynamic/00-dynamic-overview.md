# Dynamic Slides — Overview

> Source: <https://touying-typ.github.io/docs/category/dynamic-slides>

Touying's animation primitives are organised in three layers:

| Layer | Tools | Use when |
| ----- | ----- | -------- |
| **Markers** | `#pause`, `#meanwhile` | You just want incremental reveal between two adjacent blocks. |
| **Mark functions** | `#only`, `#uncover`, `#alternatives` | You need to target a *specific* subslide range outside `context` blocks. |
| **Callback style** | `#slide(repeat: N, self => {...})` + `let (only, uncover, alternatives) = utils.methods(self)` | You need full control or want to use `only`/`uncover`/`alternatives` inside `context`, `if`/`for`, raw blocks, etc. |

| File | Covers |
| ---- | ------ |
| [`01-simple.md`](./01-simple.md) | `#pause` and `#meanwhile`. |
| [`02-complex.md`](./02-complex.md) | Mark vs callback style; `#only`, `#uncover`, `#alternatives`; subslide index syntax (`"2-"`, `"!h"`, `auto`, `"h"`). |
| [`03-equation.md`](./03-equation.md) | `pause` and `meanwhile` inside math equations; `touying-equation`. |
| [`04-cover.md`](./04-cover.md) | `cover` function (default `hide`); `utils.semi-transparent-cover`; the enum/list cover hack. |
| [`05-other.md`](./05-other.md) | `touying-reducer` for CeTZ and Fletcher animations. |
| [`06-handout.md`](./06-handout.md) | `config-common(handout: true)`, `handout-subslides`, `<touying:handout>` label. |
| [`07-waypoints.md`](./07-waypoints.md) | Named timeline positions via `#waypoint(<label>)`; markers (`from-wp`, `until-wp`, `get-first`, `get-last`, `prev-wp`, `next-wp`, `not-wp`). |

## Rules of thumb

1. **`#pause` does not work inside `context { ... }`, `raw {}`, or
   nested-content callbacks** — use the callback style with
   `utils.methods(self)`.
2. **Subslide indices** are 1-based ints **or** strings: `"2"`, `"2-"`,
   `"-3"`, `"2-4"`, `"1,3"`, plus Touying-specific `"h"` (here),
   `"h-"`, `"-h"`, `"!h"` (inverse), `"!2-4"` (inverse range), `auto`.
3. **Inverse indices** (`"!h"`, `"!2-4"`) do **not** increment the
   subslide count — useful when "this should appear on every step
   *except* …".
4. **Always pass `repeat: N`** in callback style. Touying can infer
   `repeat` from `#pause` / `#only` markers used at the slide level,
   but cannot infer it through `utils.methods` bindings.
