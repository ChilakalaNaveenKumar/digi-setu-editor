# CeTZ — Drawing Package for Typst

> **CeTZ version:** 0.5.0
> **Source manual:** `guides/manual.pdf` (the full upstream PDF, 92 pages)
> **Audience:** an LLM agent that authors `.typ` files using the
> [`cetz`](https://typst.app/universe/package/cetz) package. This sub-tree is the
> CeTZ reference, organised the same way as the Typst reference under
> `../reference/`.

CeTZ ("CeTZ, ein Typst Zeichenpaket") is a drawing package for Typst whose API
is similar to Processing but with the relative coordinates and named anchors
familiar from TikZ. The canvas grows automatically, you never accidentally
draw over surrounding text, and **up is positive y**.

## What this folder contains

| Folder | Contents |
| ------ | -------- |
| [`tutorial/`](./tutorial/) | Read-this-first concept material — the canvas, draw-import idiom, coordinate systems, anchors, styling. |
| [`types/`](./types/) | Glossary of every CeTZ type used in signatures: `coordinate`, `number`, `style`, `stroke`, `vector`, `matrix`, `complex`, `bounds`, `path`, `subpath`, `segment`, `drawable`, `mark style`, `palette`, `tree node`. |
| [`reference/canvas/`](./reference/canvas/) | The single `canvas(...)` entry-point. |
| [`reference/shapes/`](./reference/shapes/) | Drawable primitives: `circle`, `rect`, `line`, `bezier`, `hobby`, `catmull`, `polygon`, `n-star`, `grid`, `content`, `arc`, `mark`, `compound-path`, `merge-path`, `rect-around`, `svg-path`, `circle-through`, `arc-through`, `bezier-through`. |
| [`reference/styling/`](./reference/styling/) | `set-style`, `fill`, `stroke`, `register-mark`. |
| [`reference/grouping/`](./reference/grouping/) | Scoping & introspection: `group`, `scope`, `hide`, `floating`, `intersections`, `anchor`, `copy-anchors`, `set-ctx`, `get-ctx`, `for-each-anchor`, `on-layer`. |
| [`reference/transformation/`](./reference/transformation/) | `set-transform`, `transform`, `rotate`, `translate`, `scale`, `set-origin`, `move-to`, `set-viewport`. |
| [`reference/projection/`](./reference/projection/) | 3-D helpers: `ortho`, `on-xy`, `on-xz`, `on-zy`, `perspective`. |
| [`reference/utility/`](./reference/utility/) | `assert-version`, `register-coordinate-resolver`. |
| [`reference/libraries/`](./reference/libraries/) | Bundled high-level libraries: `angle/`, `tree/`, `decorations/` (path & brace), `palette/`. |
| [`reference/internals/`](./reference/internals/) | Internal helper modules exposed under `cetz.*`: `complex`, `vector`, `matrix`, `coordinate`, `styles`, `process`, `drawable`, `anchor`, `mark`, `bezier`, `aabb`, `hobby`, `intersection`, `path-util`, `util`. |

## The 30-second tour

```typst
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  circle((0, 0))
  line((1, -1), (2, 1))
})
```

Three things to remember:

1. **Always import `cetz.draw: *` *inside* the `canvas` block** — many CeTZ
   functions (`line`, `rect`, `circle`, `content`, …) have the same names as
   Typst built-ins. Importing them in the canvas scope keeps them from
   overriding the Typst-level functions in your document.
2. **The canvas auto-sizes.** There is no `width`/`height` parameter on the
   canvas itself; the box just grows to fit what you draw. Pass `length:` to
   change the unit (default `1cm` per unit).
3. **`y` grows upward.** This is the opposite of the SVG / Typst layout
   convention but matches mathematical convention. `(0, 1)` is *above* `(0, 0)`.

## How each reference page is structured

Every function `.md` follows the same shape (mirroring
`../reference/visualize/01-circle.md`):

1. **Summary** — one paragraph, what the function does.
2. **Signature** — fenced `text` block with the full positional + named
   parameter list and types from the upstream manual.
3. **Parameters** — a per-arg table or bullet list capturing the descriptions
   verbatim from the manual.
4. **Styling root + Anchors** — what style key the function reads, what named
   anchors it exposes (e.g. `circle.center`, `arc.arc-end`).
5. **Pitfalls / cross-references** — agent-targeted notes (e.g. *"two of three
   angle args required"*, *"current position updates to `arc-end`"*).
6. **Runnable example** — link to the `.typ` file in the sibling
   `examples/<NN-name>/` folder.

The `.typ` examples are kept short and *each one wraps the manual snippet in a
proper `#cetz.canvas({ import cetz.draw: *; … })`* so you can `typst compile`
them as-is.

## Quick installation

CeTZ lives on the Typst package registry (`@preview` namespace), so no manual
install is needed:

```typst
#import "@preview/cetz:0.5.0"
```

The version this port targets is **0.5.0**. Pin a compatible version with
[`assert-version`](./reference/utility/01-assert-version.md) if you ship CeTZ
helpers as part of a template.

## Conceptual map (where to start)

| If you want to … | Read |
| ---------------- | ---- |
| Draw your first picture | [`tutorial/01-getting-started.md`](./tutorial/01-getting-started.md) |
| Understand the canvas envelope, units, debug | [`tutorial/02-the-canvas.md`](./tutorial/02-the-canvas.md) |
| Use coordinate systems (xyz / polar / relative / anchor / barycentric / interpolation / function) | [`tutorial/03-coordinates.md`](./tutorial/03-coordinates.md) |
| Refer to points on shapes by name (`"a.north"`, `"a.50%"`) | [`tutorial/04-anchors.md`](./tutorial/04-anchors.md) |
| Apply per-shape and inherited styling | [`tutorial/05-styling.md`](./tutorial/05-styling.md) |
| Look up one specific function | the matching folder under `reference/` |

## Notes on fidelity

- All function signatures, parameter names, parameter types, anchor lists, and
  styling roots are taken verbatim from the upstream manual (`guides/manual.pdf`).
- Where the manual's own example used `cetz.<module>.<fn>(...)` (e.g.
  `cetz.angle.angle(...)`), the example file does the same so it compiles
  without needing extra `import` statements.
- Where the manual references TikZ, math notation, or SVG path syntax, the
  cross-references are preserved.
