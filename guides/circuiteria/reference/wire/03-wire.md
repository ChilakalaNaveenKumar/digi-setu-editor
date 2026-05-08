# `wire.wire()` — Connect Two Points

Draws a wire (named, possibly bus, possibly dashed, possibly directed,
possibly slice-labelled) between two CeTZ-compatible points.

## Signature

```text
wire(
  id:            str,
  pts:           array,
  bus:           bool         = false,
  name:          none | str | array = none,
  name-pos:      str          = "middle",
  slice:         none | array = none,
  color:         color        = black,
  dashed:        bool         = false,
  style:         str          = "direct",
  reverse:       bool         = false,
  directed:      bool         = false,
  rotate-name:   bool         = true,
  zigzag-ratio:  ratio        = 50%,
  zigzag-dir:    str          = "vertical",
  dodge-y:       number       = 0,
  dodge-sides:   array        = ("east", "west"),
  dodge-margins: array        = (5%, 5%),
) -> none
```

## Parameters

- **`id`** — `str`. The wire's id, for future reference. Exposes anchors
  `<id>.start`, `<id>.end`, plus `<id>.zig` when `style: "zigzag"`.
- **`pts`** — `array`. The two endpoints, as CeTZ-compatible coordinates
  (xy tuples, relative positions, port-anchor strings, …).
- **`bus`** — `bool`. Whether the wire is a bus (multiple bits) or a simple
  signal (single bit). Default `false`.
- **`name`** — `none | str | array`. Optional name on the wire. If an array
  `(start-name, end-name)`, the first label is placed at the start, the
  second at the end. Default `none`.
- **`name-pos`** — `str`. Position of the name. One of `"middle"`,
  `"start"`, `"end"`. Default `"middle"`.
- **`slice`** — `none | array`. Optional bits-slice `(start-bit, end-bit)`.
  When set, displayed at the start of the wire. Default `none`.
- **`color`** — `color`. The stroke colour. Default `black`.
- **`dashed`** — `bool`. Whether the stroke is dashed. Default `false`.
- **`style`** — `str`. The wire's style. See
  [`04-wire-styles.md`](./04-wire-styles.md). Default `"direct"`.
- **`reverse`** — `bool`. If `true`, swap start and end (useful when the
  start point depends on the end, e.g. with perpendiculars). Default
  `false`.
- **`directed`** — `bool`. If `true`, draw an arrow at the endpoint.
  Default `false`.
- **`rotate-name`** — `bool`. If `true`, rotate the name to follow the
  wire's slope. Default `true`.
- **`zigzag-ratio`** — `ratio`. Position of the zigzag's vertical
  relative to the horizontal span (only with `style: "zigzag"`). Default
  `50%`.
- **`zigzag-dir`** — `str`. The zigzag's direction. `"vertical"` or
  `"horizontal"` (only with `style: "zigzag"`). Default `"vertical"`.
- **`dodge-y`** — `number`. Y position to dodge the wire to (only with
  `style: "dodge"`). Default `0`.
- **`dodge-sides`** — `array`. The start- and end-sides (going out of the
  connected element) of the wire (only with `style: "dodge"`). Default
  `("east", "west")`.
- **`dodge-margins`** — `array`. The start- and end-margins (i.e. space
  before dodging) of the wire (only with `style: "dodge"`). Default
  `(5%, 5%)`.

## Anchors

| Anchor | Position |
| ------ | -------- |
| `<id>.start` | First endpoint (after any `reverse:` swap). |
| `<id>.end` | Last endpoint. |
| `<id>.zig` | Corner of the zig-zag (only with `style: "zigzag"`). |

## Pitfalls

- `pts` must be a 2-element array — Circuiteria wires are point-to-point.
  Use multiple `wire(...)` calls plus `intersection(...)` for joins.
- `style: "dodge"` parameters (`dodge-y`, `dodge-sides`, `dodge-margins`)
  are silently ignored for any other style.
- The `directed` arrow is only at the *end* of the wire — set
  `reverse: true` to flip its direction without changing the visual
  topology.

## Example

See [`examples/03-wire/03-wire.typ`](./examples/03-wire/03-wire.typ).

## Related

- [`04-wire-styles.md`](./04-wire-styles.md) — the three valid `style:`
  values with side-by-side rendering.
- [`01-intersection.md`](./01-intersection.md) — mark a T-junction at a
  wire's `<id>.zig` anchor.
- [`02-stub.md`](./02-stub.md) — open-ended wires for external I/O.
