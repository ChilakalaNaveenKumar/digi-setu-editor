# 03 — Coordinate Systems

> **Source:** `manual.pdf` §3.1 (Custom Types) + cross-references throughout.

A **coordinate** in CeTZ is anything that resolves to a 3-D point on the
canvas. There are seven equivalent ways to express one. They can be mixed
freely as positional arguments to any draw function.

## 1. xyz tuple — `(x, y[, z])`

The default. `z` defaults to `0`.

```typst
circle((1, 2))         // (1, 2, 0)
circle((1, 2, 0.5))    // explicit z
```

## 2. Polar — `(angle, radius)`

The first element is an `angle`, the second a `number`.

```typst
line((0, 0), (45deg, 2))
circle((90deg, 3))
```

`0deg` points right (`+x`), `90deg` points up (`+y`).

## 3. Relative — `(rel: <coordinate> [, to: <coordinate>])`

Computed from the **previous coordinate** (or `to:` if given). The previous
coordinate is updated by every draw call; you can also set it explicitly with
[`move-to`](../reference/transformation/07-move-to.md).

```typst
circle((0, 0))
circle((rel: (1, 0)))            // 1 unit right of previous
circle((rel: (1, 0), to: "a"))   // 1 unit right of element "a"
```

The empty coordinate `()` is shorthand for the previous coordinate.

## 4. Anchor — `"<element>.<anchor>"` or dictionary form

Reference a named point on a named element. See [`04-anchors.md`](./04-anchors.md)
for the anchor catalogue.

```typst
rect((0, 0), (2, 1), name: "r")
circle("r.north")
circle((name: "r", anchor: "south-east"))
```

## 5. Path interpolation — `(<a>, <pct>, <b>)`

A 3-tuple where the middle element is a `ratio`/`number` produces the point
that fraction of the way from `a` to `b`. Both endpoints can themselves be
anchor strings.

```typst
line((0, 0), (3, 1), name: "l")
circle(("l.start", 50%, "l.end"), radius: .1)   // midpoint of the line
```

## 6. Barycentric — `(barycentric: (a: 1, b: 0.5))`

Weighted combination of named anchors. CeTZ resolves each key as an anchor
coordinate and computes the weighted centroid.

## 7. Function form — `c => <coordinate>`

Pass a function `(prev) => <coordinate>` to compute a coordinate from the
previous point at resolve time. Useful for running computations (e.g.
`cetz.vector.add`) without dropping into `get-ctx`.

## Updating the "previous coordinate"

After every draw call CeTZ updates the previous coordinate to the most-natural
end of the just-drawn shape (e.g. `arc-end` for `arc`, the second positional
for `line`). Use:

| To … | Use |
| ---- | --- |
| Set the previous coordinate manually | [`move-to(pt)`](../reference/transformation/07-move-to.md) |
| Read the previous coordinate inside a snippet | the empty tuple `()` |

## Resolving by hand

Sometimes you need the resolved vector — e.g. to feed it into
`cetz.vector.add`. Use [`cetz.coordinate.resolve`](../reference/internals/coordinate/02-resolve.md)
inside a [`get-ctx`](../reference/grouping/09-get-ctx.md) callback:

```typst
line((0, 0), (1, 1), name: "l")
get-ctx(ctx => {
  let (ctx, a, b) = cetz.coordinate.resolve(ctx, "l.start", "l.end")
  content("l.start", [#a], frame: "rect", stroke: none, fill: white)
  content("l.end", [#b], frame: "rect", stroke: none, fill: white)
})
```

## Custom resolvers

Push your own resolver for unrecognised coordinate dictionaries (e.g. a `log`
key for log-scale plotting):

```typst
register-coordinate-resolver((ctx, c) => {
  if type(c) == dictionary and "log" in c {
    c = c.log.map(n => calc.log(n, base: 10))
  }
  return c
})
circle((log: (10, 1e-6)), radius: .25)
```

See [`register-coordinate-resolver`](../reference/utility/02-register-coordinate-resolver.md).
