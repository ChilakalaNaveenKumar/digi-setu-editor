# Element — Overview

The element module ships ready-made block-shaped circuit primitives.
Every element accepts the same family of base parameters (origin, size,
ports, fill, stroke, id, debug); the element-specific functions add a
custom shape and / or extra knobs.

| Function | Purpose | Page |
| -------- | ------- | ---- |
| `elmt(...)` | The base element. Drawn from a `draw-shape` callback; all the other element functions are thin wrappers around this. | [`01-elmt.md`](./01-elmt.md) |
| `alu(...)` | Arithmetic logic unit shape with two inputs (`in1`, `in2`) on the west side and one output (`out`) on the east. | [`02-alu.md`](./02-alu.md) |
| `block(...)` | A rectangular block with arbitrary user-defined ports on each side, optional clock port, and optional name. | [`03-block.md`](./03-block.md) |
| `extender(...)` | A bit-width extender: trapezoidal shape with one input (`in`) on the west and one output (`out`) on the east. | [`04-extender.md`](./04-extender.md) |
| `multiplexer(...)` | A trapezoidal multiplexer with N inputs (binary-indexed, or named) and one output. | [`05-multiplexer.md`](./05-multiplexer.md) |
| `group(...)` | A labelled border drawn around a body of other elements. | [`06-group.md`](./06-group.md) |

> `gate(...)`, `gate-and(...)`, etc. are documented under
> [`../gates/`](../gates/00-gates-overview.md). They are also re-exported
> as `element.gate(...)`, `element.gate-and(...)`, … so you can write
> either `gates.gate-and(...)` or `element.gate-and(...)`.

## The shared parameter family

Every element function accepts (a subset of) these common arguments —
described in detail on [`01-elmt.md`](./01-elmt.md):

```text
x:           number | dictionary
y:           number | dictionary
w:           number
h:           number
name:        none | str
name-anchor: str
fill:        none | color
stroke:      stroke
id:          str
debug:       dictionary
```

Plus, on most elements:

```text
ports:         dictionary
ports-margins: dictionary
auto-ports:    bool
ports-y:       dictionary
```

## The `<id>-port-<port-id>` anchor convention

Once an element has been drawn with `id: "alu"` and a port `(id: "out")`
on its east side, the anchor `"alu-port-out"` can be passed to any
`wire.wire(...)`, `wire.stub(...)`, or `wire.intersection(...)` call.
The literal `-port-` infix is mandatory.

## Compass anchors

Every element also exposes the standard CeTZ compass anchors on its
bounding box: `<id>.north`, `<id>.east`, `<id>.south`, `<id>.west`,
`<id>.center`. Use these to align other elements via `(rel: ..., to: ...)`
and `(from: ..., to: ...)` `x:` / `y:` dictionaries.

## Pitfalls

- `id` defaults to the empty string `""`. If you skip it you cannot
  reference the element's anchors. **Always set `id:`.**
- `auto-ports: false` puts the burden of placing the ports on the
  `draw-shape:` callback. The shipped elements all use `auto-ports: true`.
- `debug: (ports: true)` shows red dots on every port — invaluable when
  hunting "anchor not found" errors.
