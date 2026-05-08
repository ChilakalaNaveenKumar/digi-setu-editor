# 8 — Touying integration

[Touying](https://touying-typ.github.io/) is a Typst slide framework
that supports `pause`, `uncover`, `only`, and `alternatives` for
incrementally revealing content. Fletcher integrates with Touying via
a **reducer** that interprets these primitives inside `diagram(..)`.

## Recipe

```typst
#import "@preview/touying:0.5.5": *
#import "@preview/fletcher:0.5.8" as fletcher: node, edge

#show: themes.simple.simple-theme.with(aspect-ratio: "16-9")

#let diagram = touying-reducer.with(
  reduce: fletcher.diagram,
  cover: fletcher.hide,
)

#slide(repeat: 6, self => {
  let (uncover, only, alternatives) = utils.methods(self)
  diagram(
    node((0, 0), name: <A>)[$A$],
    pause,
    edge("->"),
    node((1, 0), name: <B>)[$B$],
    pause,
    edge("->"),
    node((2, 0), name: <C>)[$C$],
    only("4,6", edge(<A>, "~", <B>, bend: 40deg, stroke: red)),
    only("5,6", edge(<B>, "~", <C>, bend: 40deg, stroke: green)),
    only("6", edge(<C>, "~", <A>, bend: 40deg, stroke: blue)),
  )
})
```

The key call is:

```typst
#let diagram = touying-reducer.with(
  reduce: fletcher.diagram,
  cover: fletcher.hide,
)
```

This rewires `diagram` to first interpret Touying primitives
(`pause`, `uncover`, `only`, `alternatives`) and then forward the
result to `fletcher.diagram`.

`cover: fletcher.hide` tells Touying how to "cover" hidden content
without affecting layout — `fletcher.hide(content, bounds: true)`
reserves the bounding box so revealing later doesn't shift the
diagram.

## Notes

- This recipe lives in your *Touying slide file*, not in the diagram
  itself. The `tutorial/examples/08-touying/` directory has a runnable
  static stand-in (no actual slides) so the example compiles outside a
  Touying project.
- For a pure document (no Touying), use `fletcher.hide(content)`
  directly — see [`reference/internals/draw/09-hide.md`](../reference/internals/draw/09-hide.md).

## Pitfalls

- The reducer must be assigned to a *new local* `diagram` —
  re-importing `fletcher.diagram` directly will not interpret
  `pause` / `uncover`.
- Touying expects the reducer's output to itself accept `repeat:` and
  the standard slide methods. Don't wrap the reducer's output in a
  function.
- For a single static fallback render, just use `fletcher.diagram`
  without the reducer; everything still works.

## Done!

You've finished the tutorial. Continue to the
[reference](../reference/main/00-main-overview.md) for full function
signatures.
