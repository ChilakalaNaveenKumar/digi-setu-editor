# 05 — Styling

> **Source:** `manual.pdf` §3.3 + §4.3

CeTZ has two universal style keys plus per-element style trees. They cascade
the same way Typst's `set` rules do — values you set later overwrite earlier
ones, and they reset at the end of their containing scope (`group`, `scope`,
or the canvas body).

## Universal keys

Every drawing element accepts:

| Key | Default | Type |
| --- | ------- | ---- |
| `fill` | `none` | `color`, `gradient`, `tiling`, or `none` |
| `stroke` | `black` | `none`, `auto`, `length`, `color`, `length + color`, `dictionary`, or a `stroke()` object |

When you set `fill` on an element, **the default stroke is *not* removed**
(unlike Typst's `rect`/`circle`).

## Per-call vs. inherited

Pass a key as a named argument to one draw call:

```typst
circle((0, 0), fill: red, stroke: 2pt + black)
rect((1, 0), (3, 1))      // unaffected
```

…or use [`set-style(...)`](../reference/styling/01-set-style.md) /
[`fill(...)`](../reference/styling/02-fill.md) /
[`stroke(...)`](../reference/styling/03-stroke.md) to change the inherited
default for everything that follows in this scope:

```typst
fill(red)
stroke(2pt + black)
circle((0, 0))    // inherits both
rect((1, 0), (3, 1))   // inherits both
```

## Element-rooted style trees

Each shape advertises a **styling root** (`circle`, `rect`, `arc`, `mark`,
`content`, …). Setting that root from `set-style` configures defaults for
every instance of that shape in the current scope:

```typst
set-style(circle: (radius: .3, fill: blue.lighten(50%)))
circle((0, 0))        // 0.3-radius blue
circle((1, 0))        // same
circle((2, 0), fill: red)   // override per call
```

Roots can be nested — `mark` is a sub-style on `line`, `bezier`, `catmull`,
…, so `set-style(line: (mark: (end: ">")))` configures end-marks on every
following line.

## Style folding rules (the practical version)

1. Values resolved from set-style apply to all descendant elements in scope.
2. Per-call named arguments overwrite inherited values.
3. `auto` on any field inherits from the nearest ancestor that names it.
4. Sub-dictionaries are recursively merged (so partial styling like
   `(stroke: (paint: red))` only changes `paint`, not `thickness` or `dash`).

The full algorithm lives in
[`cetz.styles.resolve`](../reference/internals/styles/01-resolve.md).

## Examples

### Per-call

```typst
circle((0, 0), fill: aqua, stroke: 2pt + black)
```

### Set defaults inside a group

```typst
group({
  set-style(stroke: 2pt + red, fill: white)
  circle((0, 0))
  rect((1, 0), (2, 1))
})
// Outside the group: defaults restored.
```

### Style root for one shape only

```typst
set-style(rect: (radius: 25%, fill: yellow.lighten(50%)))
rect((0, 0), (1, 1))
rect((2, 0), (3, 1))
```

### Layered inheritance

```typst
set-style(stroke: 1pt + gray)
group({
  set-style(stroke: 2pt + red)   // overrides for this group only
  line((0, 0), (1, 0))
})
line((0, 1), (1, 1))             // back to gray
```

## Marks (arrowheads)

Anything that draws a path supports an optional `mark:` sub-style:

```typst
line((0, 0), (1, 0), mark: (end: ">"))
line((0, .5), (1, .5), mark: (start: "<", end: ">>"))
```

Register your own with [`register-mark(...)`](../reference/styling/04-register-mark.md).
The full mark dictionary (length, width, inset, sep, …) is documented under
[`internals/mark/`](../reference/internals/mark/).

## See also

- [`reference/styling/`](../reference/styling/) — `set-style`, `fill`, `stroke`,
  `register-mark`.
- [`reference/grouping/01-group.md`](../reference/grouping/05-group.md) — how
  scope boundaries reset style.
- [`reference/internals/styles/01-resolve.md`](../reference/internals/styles/01-resolve.md)
  — exact merge algorithm.
