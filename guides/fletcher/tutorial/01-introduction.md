# 1 — Introduction

Fletcher is a Typst package for **diagrams with arrows** —
commutative diagrams, signal flow, state machines, block diagrams.
The drawing primitives are deliberately small: a `node()`, an `edge()`,
and a `diagram()` envelope that lays them out on an elastic grid.

If you have used `tikz-cd`, `quiver`, or XY-pic in LaTeX, the syntax
will feel very familiar.

## Install

```typst
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
```

For shapes and the `MARKS` registry, also import:

```typst
#import fletcher.shapes: diamond, hexagon, brace
// fletcher.MARKS, fletcher.cetz, etc.
```

## Your first diagram

```typst
#diagram(
  node((0, 0), $A$),
  edge("->"),
  node((1, 0), $B$),
)
```

A flat sequence of `node` / `edge` items. The single edge here uses
auto-snapping (`auto, auto`) to connect the *previous* and *next*
node, so it goes from `A` to `B`.

See [`examples/01-introduction/01-introduction.typ`](examples/01-introduction/01-introduction.typ).

## Two ways to build a diagram

```typst
// 1. Free-form — code mode
#diagram(spacing: 2cm, {
  let (A, B) = ((0,0), (1,0))
  node(A, $cal(A)$)
  node(B, $cal(B)$)
  edge(A, B, $F$, "->", bend: +35deg)
  edge(A, B, $G$, "->", bend: -35deg)
})

// 2. Math-mode — concise
#diagram($
  A edge(->) & B \
  C edge(->) & D
$)
```

## What you can put in `diagram(..)`

| Item | Meaning |
| ---- | ------- |
| `node(coord, label, ..options)` | Draws a node at `coord`. |
| `edge(..vertices, marks, label, ..options)` | Draws an edge between vertices. |
| Plain content | Inserted as a comment / floating text. |
| Math equations | Auto-translated into `node` / `edge` calls. |

Code blocks `{ ... }` may contain loops, lets, and any combination of
the above — they're flattened into the children list.

## Next

[`02-diagrams-and-coordinates.md`](02-diagrams-and-coordinates.md) —
elastic vs absolute coordinates.
