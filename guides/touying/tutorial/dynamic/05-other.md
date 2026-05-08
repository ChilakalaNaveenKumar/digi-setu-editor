# Dynamic 05 — Other Animations (`touying-reducer` for CeTZ / Fletcher)

> Source: <https://touying-typ.github.io/docs/tutorials/dynamic/other>

Touying's `touying-reducer` adapts foreign drawing primitives (CeTZ,
Fletcher, …) so that `#pause`, `#meanwhile`, `only`, `uncover` work
*inside* their canvases.

## Setting up the reducers

```typst
#import "@preview/touying:0.7.3": *
#import themes.university: *
#import "@preview/cetz:0.5.0"
#import "@preview/fletcher:0.5.8" as fletcher: node, edge

// CeTZ binding
#let cetz-canvas = touying-reducer.with(
  reduce: cetz.canvas,
  cover: cetz.draw.hide.with(bounds: true),
)

// Fletcher binding
#let fletcher-diagram = touying-reducer.with(
  reduce: fletcher.diagram,
  cover: fletcher.hide,
)
```

The `cover:` parameter tells the reducer **how to hide** an element
without losing its bounding box. CeTZ uses `cetz.draw.hide.with(bounds:
true)`; Fletcher uses `fletcher.hide`.

## Simple animations

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

Note the `(pause,)` syntax — *single-element tuple containing the marker*.
That is because the CeTZ canvas body is an array of draw commands, not a
content block; the reducer scans the array for `pause` / `meanwhile`
markers.

```typst
#slide[
  Fletcher in Touying:
  #fletcher-diagram(
    node-stroke: .1em,
    node-fill: gradient.radial(blue.lighten(80%), blue,
                               center: (30%, 20%), radius: 80%),
    spacing: 4em,
    edge((-1, 0), "r", "-|>", `open(path)`, label-pos: 0, label-side: center),
    node((0, 0), `reading`, radius: 2em),
    edge((0, 0), (0, 0), `read()`, "--|>", bend: 130deg),
    pause,
    edge(`read()`, "-|>"),
    node((1, 0), `eof`, radius: 2em),
    pause,
    edge(`close()`, "-|>"),
    node((2, 0), `closed`, radius: 2em, extrude: (-2.5, 0)),
    edge((0, 0), (2, 0), `close()`, "-|>", bend: -40deg),
  )
]
```

For Fletcher, `pause` is just a comma-separated argument — Fletcher
already takes a flat var-args list of nodes / edges.

## `only`, `uncover`, `alternatives`

These work *position-based* inside CeTZ / Fletcher. For CeTZ:

```typst
#slide[
  #cetz-canvas({
    import cetz.draw: *

    rect((0, 0), (5, 5))
    (pause,)
    rect((0, 0), (1, 1))
    (uncover(3, {
      rect((1, 1), (2, 2))
      rect((2, 2), (3, 3))
    }),)
    (only(3, line((0, 0), (2.5, 2.5), name: "line")),)
  })
]
```

For Fletcher:

```typst
#fletcher-diagram(
  node-stroke: .1em,
  spacing: 4em,
  node((0, 0), [A], radius: 2em),
  pause,
  uncover("1-2", edge((0, 0), (1, 0), "-|>", stroke: blue)),
  uncover("2-", node((1, 0), [B], radius: 2em)),
  only(3, node((0, 1), [tmp], radius: 1em, fill: orange)),
)
```

> **Note.** `only` *drops* the draw command (so its position is freed up
> in CeTZ); `uncover` keeps the bounds. Visually identical for fixed-
> position diagrams; under the hood they differ.

> **Note.** Commands like `effect:` and `item-by-item:` may not work as
> expected inside reducers.

## Callback-style bindings (avoid the `(cmd,)` tuples)

If you don't want to write `(cmd,)` tuples in CeTZ, use callback style and
redefine `uncover` locally:

```typst
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

You must manually count subslides via `repeat:` — this is the trade-off
for not using the reducer.

This recipe also works for Fletcher, but the reducer pattern is usually
preferred there.

## Example

See [`examples/05-other/05-other.typ`](./examples/05-other/05-other.typ)
and [`examples/05-other-fletcher/05-other-fletcher.typ`](./examples/05-other-fletcher/05-other-fletcher.typ).

## Pitfalls

- For CeTZ inside `cetz-canvas`, animation markers must be written as a
  single-element tuple: `(pause,)`, `(only(2, x),)`, `(uncover("2-",
  x),)`. CeTZ's body is an array; a bare `pause` is interpreted as a
  drawable.
- For Fletcher, markers are just bare arguments: `pause`, `uncover(...)`,
  `only(...)` — no tuple wrapping.
- The `cover:` argument to `touying-reducer.with(...)` is mandatory —
  this is what tells the reducer how to hide elements.
