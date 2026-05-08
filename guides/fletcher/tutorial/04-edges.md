# 4 — Edges

`edge(..vertices, marks, label, ..options)` connects two (or more)
coordinates. Edges auto-snap to nearby nodes and can carry labels,
bend, take corners, or follow a multi-segment polyline.

## Specifying vertices

| Form | Meaning |
| ---- | ------- |
| `edge(from, to, ..)` | Two explicit vertices. |
| `edge(to, ..)` | Same as `edge(auto, to, ..)` — snap from previous node. |
| `edge(..)` | `edge(auto, auto, ..)` — snap to nearest nodes both sides. |
| `edge(from, v1, v2, ..vs, to, ..)` | Multi-vertex `"poly"` edge. |

The first vertex must be explicit (or `auto`); every subsequent vertex
may be a **relative coord shorthand**:

| Shorthand | Meaning |
| --------- | ------- |
| `"u"`, `"d"`, `"l"`, `"r"` | up, down, left, right (single cell). |
| `"n"`, `"s"`, `"e"`, `"w"` | north / south / east / west aliases. |
| `"ur"`, `"dl"`, … | combinations. |
| `"r,d,r"` | comma-separated path. |

## Marks (arrowheads)

The most common mark string is the third positional argument:

```typst
edge((0,0), (1,0), "->")        // arrow at end
edge((0,0), (1,0), "<-", "rr")  // double-cell jump with arrow at start
edge((0,0), (1,0), "<=>")       // double-stroke double-headed
```

Full mark grammar in [`05-marks-and-arrows.md`](05-marks-and-arrows.md).

## Edge types

`kind: "line" | "arc" | "poly"`. Inferred from `bend:` (→ arc) or
multiple vertices (→ poly).

```typst
#diagram(
  edge((0,0), (1,1), "->", `line`),
  edge((2,0), (3,1), "->", bend: -30deg, `arc`),
  edge((4,0), (4,1), (5,1), (6,0), "->", `poly`),
)
```

## Labels

```typst
edge((0,0), (1,0), "->", $f$)
edge((0,0), (1,0), $f$, "->")             // same — order doesn't matter
edge((0,0), (1,0), $f$, "->", label-side: left)
edge((0,0), (1,0), $f$, "->", label-pos: 0.25)
```

Useful label options:

| Option | Default | Effect |
| ------ | ------- | ------ |
| `label-side` | `auto` | `left`, `right`, `center`. |
| `label-pos`  | `50%`  | Position along edge (`0`..`1` or `(segment, frac)`). |
| `label-sep`  | `0.4em` | Gap between edge and label anchor. |
| `label-angle` | `0deg` | Rotation, or `auto` / `top` / `right` / … |
| `label-fill` | `auto` | Background; `true` uses `crossing-fill`. |

## Snap

By default, the *first* and *last* vertices snap to nearby nodes. To
override:

```typst
edge((0,0), (1,1), "->", snap-to: (<a>, none))   // start snaps to <a>, end doesn't
```

See [`examples/04-edges/04-edges.typ`](examples/04-edges/04-edges.typ).

## Pitfalls

- A single edge with `bend: 30deg` is rendered as an arc; with no
  `bend`, the same vertices give a straight line.
- The relative-shorthand string applies to **vertices after the first**
  — the first vertex must be a real coord (or `auto`).
- `auto, auto` only works when the edge sits *between* two nodes in
  the diagram body. Standalone edges need explicit vertices.

## Next

[`05-marks-and-arrows.md`](05-marks-and-arrows.md) — the mark
shorthand grammar.
