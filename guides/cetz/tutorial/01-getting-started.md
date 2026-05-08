# 01 — Getting Started

> **CeTZ version:** 0.5.0 · **Source:** `manual.pdf` §1–§2

CeTZ is invoked from any Typst document by importing the package and wrapping
your drawing code in a `canvas { ... }` block. This page walks through the
absolute minimum.

## Hello, CeTZ

```typst
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  // Draw a circle
  circle((0, 0))
  // Draw a line
  line((1, -1), (2, 1))
})
```

See it as an isolated example: [`examples/01-hello-cetz/01-hello-cetz.typ`](./examples/01-hello-cetz/01-hello-cetz.typ).

## Why import `cetz.draw: *` *inside* the canvas

Several CeTZ draw functions share names with Typst built-ins (`line`, `rect`,
`circle`, `content`, …). If you imported them at the top of the file you would
override the Typst-level functions everywhere else. Importing them inside the
canvas block scopes the override to just the drawing.

```typst
#cetz.canvas({
  import cetz.draw: *      // line/rect/circle now refer to CeTZ
  rect((0, 0), (1, 1))
})

This paragraph still uses Typst's `rect`, `line`, etc.
```

## Convention used in the rest of this folder

From here on, **only the body of the canvas block is shown** in inline code
samples — assume the same outer wrapper:

```typst
#import "@preview/cetz:0.5.0"
#cetz.canvas({
  import cetz.draw: *
  // <snippet here>
})
```

Each `examples/<n>/<n>.typ` file in the reference folders is the *full,
compilable* version with the wrapper restored.

## Coordinates 30-second cheat sheet

| Form | Example | Meaning |
| ---- | ------- | ------- |
| xyz tuple | `(1, 2)` or `(1, 2, 0.5)` | Cartesian, z optional |
| Polar | `(45deg, 2)` | angle, then distance |
| Relative | `(rel: (0, 1))` | offset from previous coordinate |
| Anchor | `"a.north"` | named point on element `a` |
| Anchor (dict) | `(name: "a", anchor: "north")` | same, dictionary form |
| Path interp | `("a.start", 50%, "a.end")` | 50 % of the way along that segment |

`(0, 0)` is the canvas origin. **Up is positive y** — the opposite of the
SVG/Typst-layout convention.

## Next steps

- [`02-the-canvas.md`](./02-the-canvas.md) — the canvas envelope, units, debug
  rendering, baseline.
- [`03-coordinates.md`](./03-coordinates.md) — the seven coordinate systems in
  detail.
- [`04-anchors.md`](./04-anchors.md) — how every shape exposes named points.
- [`05-styling.md`](./05-styling.md) — `set-style`, root style trees, inherited
  values.
