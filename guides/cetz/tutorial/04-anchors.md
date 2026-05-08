# 04 — Anchors

Every named element exposes a small dictionary of named **anchors** — points
on or around the element you can reference later as coordinates.

```typst
rect((0, 0), (2, 1), name: "r")
circle("r.north", radius: .1)
line("r.south-west", "r.north-east")
```

## How to name an element

Pass `name: "<id>"` to any draw function that accepts it (every shape does).
The id can then be used as the prefix of any anchor coordinate:

| Form | Example |
| ---- | ------- |
| `"<name>"` alone | resolves to the element's `default` anchor |
| `"<name>.<anchor>"` | a specific anchor |
| `(name: "<name>", anchor: "<anchor>")` | dictionary equivalent |
| Implicit nested anchor | `"a.b.north"` (element `b` lives inside group `a`) |

## Anchor families

CeTZ defines four families. Each shape advertises which families it supports
on its reference page.

### Border anchors (compass)

Available on most boxed shapes (`rect`, `circle`, `ellipse`, group, …):
`center`, `north`, `north-east`, `east`, `south-east`, `south`, `south-west`,
`west`, `north-west`. Plus interpolated forms: any angle expression like
`<rect-name>.45deg` resolves to where a ray from the centre exits the border.

### Path anchors

Available on every path-shaped element (`line`, `bezier`, `arc`, `catmull`,
`hobby`, `polygon`, `n-star`, `compound-path`, `merge-path`, `svg-path`):

| Anchor | Position |
| ------ | -------- |
| `start` | first point of the path |
| `end` | last point of the path |
| `mid` | 50 % along the path's arc-length |
| `<percentage>` | arbitrary `<n>%` along the path |

### Element-specific anchors

Some shapes name extra points:

- `arc` → `arc-start`, `arc-end`, `arc-center`, `chord-center`, `origin`.
- `bezier` → `ctrl-0`, `ctrl-1`, …
- `catmull` / `hobby` → `pt-0`, `pt-1`, … (one per input point).
- `content` → `mid`, `mid-east`, `mid-west`, `base`, `base-east`, `base-west`,
  `text`.
- `circle-through` → `a`, `b`, `c` (the three input points).

### Custom anchors

Inside a `group` you can register your own anchor with [`anchor`](../reference/grouping/06-anchor.md):

```typst
group(name: "g", {
  circle((0, 0))
  anchor("here", (.4, .1))
  circle("here", radius: .1, fill: red)
})
circle("g.here", radius: .05, fill: green)
```

`anchor("default", ...)` overrides the group's `default` anchor (otherwise
`center`).

You can pull anchors from one element into the surrounding group with
[`copy-anchors`](../reference/grouping/07-copy-anchors.md).

## Discovering anchors at runtime

Use [`for-each-anchor`](../reference/grouping/10-for-each-anchor.md) to iterate
every named anchor on an element:

```typst
rect((0, 0), (2, 2), name: "r")
for-each-anchor("r", exclude: ("start", "mid", "end"), name => {
  content((), box(inset: 1pt, fill: white, text(8pt, [#name])), angle: -30deg)
})
```

## Computing intersection anchors

[`intersections("i", { ... })`](../reference/grouping/03-intersections.md)
calculates every intersection between the drawables in its body and turns
them into the anchors `"i.0"`, `"i.1"`, …:

```typst
intersections("i", {
  circle((0, 0))
  line((-1, 0), (1, 0))
})
circle("i.0", radius: .05, fill: red)
circle("i.1", radius: .05, fill: red)
```

## Anchor of an anchor — element nesting

`group(name: "outer", { circle((), name: "inner") })` produces nested
elements; reach through with `"outer.inner.north"`. The implicit
`(name: "outer", anchor: "inner.north")` dictionary form works too.
