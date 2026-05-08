# CeTZ Tutorial — Overview

Read these in order before diving into the per-function pages under
[`../reference/`](../reference/).

| File | Covers |
| ---- | ------ |
| [`01-getting-started.md`](./01-getting-started.md) | Importing the package, the `canvas { … }` block, the `cetz.draw: *` idiom. |
| [`02-the-canvas.md`](./02-the-canvas.md) | The canvas envelope: auto-sizing, `length:`, `padding:`, `debug:`, baseline, background. |
| [`03-coordinates.md`](./03-coordinates.md) | The seven coordinate systems (xyz, polar, relative, anchor, path-interp, barycentric, function form) and how the *previous coordinate* updates. |
| [`04-anchors.md`](./04-anchors.md) | Naming elements, compass anchors, path anchors, custom anchors via `anchor(...)`, intersection anchors. |
| [`05-styling.md`](./05-styling.md) | Per-call vs. `set-style` defaults, style roots (`circle`, `rect`, `mark`, …), folding rules, marks. |

After this you should be comfortable navigating any function under
`../reference/`. Each function's `.md` page assumes you know:

1. The drawing happens inside `cetz.canvas({ import cetz.draw: *; … })`.
2. `(x, y)` coordinates have *y growing upward*.
3. `name: "id"` plus `"id.<anchor>"` is how shapes refer to one another.
4. `set-style(<root>: (key: value))` sets defaults for a shape root.
