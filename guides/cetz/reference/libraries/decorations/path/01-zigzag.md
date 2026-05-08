# `cetz.decorations.zigzag()` — Zigzag / Saw-Tooth Wave

Draws a zig-zag (or saw-tooth) wave along a path.

## Signature

```text
cetz.decorations.zigzag(
  target: drawable,
  name:   none | string = none,
  close:  auto | bool   = auto,
  ..style: style,
)
```

## Parameters

- **`target`** — the path to decorate (e.g. `line((0,0), (2,1))`).
- **`close`** — close the resulting path.
- **`name`** — element name.
- **`segments`** *(style)* / **`segment-length`** *(style)* — number /
  length of teeth.
- **`amplitude`** *(style)* — perpendicular height of the wave.
- **`factor`** *(style, ratio)* — triangle midpoint between start and end.
  `0%` = falling sawtooth, `100%` = rising sawtooth, `50%` = symmetric
  triangle wave.
- **`start`** / **`stop`** *(style, ratio)* — start / end percentage along
  the path.

## Styling

- **Root:** `zigzag`

## Example

See [`examples/01-zigzag/01-zigzag.typ`](./examples/01-zigzag/01-zigzag.typ).
