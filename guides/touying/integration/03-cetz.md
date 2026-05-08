# Integration — CeTZ

> Source: <https://touying-typ.github.io/docs/integration/cetz>
>
> Package: [`cetz`](https://typst.app/universe/package/cetz) v0.5.0
>
> See also: [`../../cetz/`](../../cetz/) for the full CeTZ reference.

Touying integrates with [CeTZ](https://github.com/cetz-package/cetz)
through `touying-reducer`, which adds `pause` / `meanwhile` / `only` /
`uncover` to CeTZ canvases.

## Setup

```typst
#import "@preview/touying:0.7.3": *
#import themes.metropolis: *
#import "@preview/cetz:0.5.0"
#import "@preview/fletcher:0.5.8" as fletcher: node, edge

// CeTZ + Fletcher Touying bindings
#let cetz-canvas = touying-reducer.with(
  reduce: cetz.canvas,
  cover: cetz.draw.hide.with(bounds: true),
)
#let fletcher-diagram = touying-reducer.with(
  reduce: fletcher.diagram,
  cover: fletcher.hide,
)

#show: metropolis-theme.with(aspect-ratio: "16-9")
```

## Simple animation

Inside the canvas body, animation markers are written as
**single-element tuples** — `(pause,)`, `(only(2, x),)`, `(uncover("2-",
x),)`. CeTZ's body is an array of draw commands; the reducer scans this
array for markers.

```typst
#slide[
  Cetz in Touying:
  #cetz-canvas({
    import cetz.draw: *

    rect((0, 0), (5, 5))
    (pause,)
    rect((0, 0), (1, 1))
    rect((1, 1), (2, 2))
    rect((2, 2), (3, 3))
    (pause,)
    line((0, 0), (2.5, 2.5), name: "line")
  })
]
```

For Fletcher, see [`04-fletcher.md`](./04-fletcher.md).

## `only` and `uncover`

```typst
#import "@preview/touying:0.7.3": *
#import "@preview/cetz:0.5.0"
#import themes.simple: *

#show: simple-theme.with(aspect-ratio: "16-9")

#slide(repeat: 3, self => [
  #let (uncover, only, alternatives) = utils.methods(self)

  Cetz in Touying in subslide #self.subslide:
  #cetz.canvas({
    import cetz.draw: *
    let uncover = uncover.with(cover-fn: hide.with(bounds: true))

    rect((0, 0), (5, 5))
    uncover("2-3", {
      rect((0, 0), (1, 1))
      rect((1, 1), (2, 2))
      rect((2, 2), (3, 3))
    })
    only(3, line((0, 0), (2.5, 2.5), name: "line"))
  })
])
```

Note this version uses **callback-style** (`#slide(repeat: 3, self =>
[...])`) and **`cetz.canvas` directly** rather than `cetz-canvas`. It
trades the reducer's auto-counting for the ability to use `only` /
`uncover` as bare CeTZ commands instead of `(only(...),)` tuples.

## Example

See [`examples/03-cetz/03-cetz.typ`](./examples/03-cetz/03-cetz.typ) and
[`examples/03-cetz-callback/03-cetz-callback.typ`](./examples/03-cetz-callback/03-cetz-callback.typ).

## Pitfalls

- Inside `cetz-canvas` (the reducer-wrapped form), animation markers
  **must** be written as a one-element tuple: `(pause,)`. A bare `pause`
  will be interpreted by CeTZ as a drawable name and panic.
- The `cover:` parameter of `touying-reducer.with(...)` *must* be
  `cetz.draw.hide.with(bounds: true)` for CeTZ — `bounds: true` keeps
  the bounding box, which is essential for layout.
- The callback-style `cetz.canvas` lets you write
  `let uncover = uncover.with(cover-fn: hide.with(bounds: true))` so
  `uncover(...)` drops a CeTZ-native hide command.
- For static (non-animated) CeTZ work, you don't need touying-reducer at
  all — just call `cetz.canvas({ ... })` directly.
