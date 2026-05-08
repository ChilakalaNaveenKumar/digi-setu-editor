# Integration — Fletcher

> Source: <https://touying-typ.github.io/docs/integration/fletcher>
>
> Package: [`fletcher`](https://typst.app/universe/package/fletcher) v0.5.8
>
> See also: [`../../fletcher/`](../../fletcher/) for the full Fletcher reference.

Touying integrates with [Fletcher](https://github.com/Jollywatt/typst-fletcher)
through `touying-reducer`, which adds `pause` / `meanwhile` to Fletcher
diagrams.

## Setup

```typst
#import "@preview/touying:0.7.3": *
#import themes.metropolis: *
#import "@preview/cetz:0.5.0"
#import "@preview/fletcher:0.5.8" as fletcher: node, edge

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

## Animated Fletcher diagram

```typst
#slide[
  Fletcher in Touying:
  #fletcher-diagram(
    node-stroke: .1em,
    node-fill: gradient.radial(blue.lighten(80%), blue,
                               center: (30%, 20%), radius: 80%),
    spacing: 4em,
    edge((-1, 0), "r", "-|>", `open(path)`,
         label-pos: 0, label-side: center),
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

Notice that `pause` is just a comma-separated argument inside
`fletcher-diagram(...)` — Fletcher already takes a flat var-args list,
so no tuple wrapping needed (unlike CeTZ).

## Callback-style with `uncover`

For `only` / `uncover` / `alternatives` inside Fletcher, the pattern
mirrors CeTZ:

```typst
#import "@preview/touying:0.7.3": *
#import "@preview/fletcher:0.5.8" as fletcher: diagram, edge, node

#show: themes.simple.simple-theme.with(aspect-ratio: "16-9")

#let diagram = touying-reducer.with(
  reduce: fletcher.diagram,
  cover: fletcher.hide,
)

#slide(repeat: 6, self => {
  let (uncover, only, alternatives) = utils.methods(self)
  let uncover = uncover.with(cover-fn: fletcher.hide)

  diagram(
    node((0, 0), name: <A>)[$A$],
    pause,
    edge("->"),
    node((1, 0), name: <B>)[$B$],
    pause,
    edge("->"),
    node((2, 0), name: <C>)[$C$],
    uncover("4,6", edge(<A>, "~", <B>, bend: 40deg, stroke: red)),
    only("5,6", edge(<B>, "~", <C>, bend: 40deg, stroke: green)),
    only("6", edge(<C>, "~", <A>, bend: 40deg, stroke: blue)),
  )
})
```

The crucial line is `let uncover = uncover.with(cover-fn: fletcher.hide)`
— it forces `uncover` to use Fletcher's hide function rather than the
default Typst `hide`.

## Example

See [`examples/04-fletcher/04-fletcher.typ`](./examples/04-fletcher/04-fletcher.typ).

## Pitfalls

- Fletcher edges don't keep bounds the way CeTZ does — use
  `fletcher.hide` (no `bounds:` arg).
- For animation **inside** the diagram, prefer `pause` and `uncover` over
  `only` — `only` removes nodes from layout entirely, which can shift
  the rest of the diagram.
- The `repeat: N` count is *manual* in callback style. With the reducer
  (`fletcher-diagram(...)`), Touying counts `pause` markers automatically.
