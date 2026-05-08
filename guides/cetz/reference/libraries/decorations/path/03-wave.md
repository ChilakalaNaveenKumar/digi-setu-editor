# `cetz.decorations.wave()` — Sinusoidal Wave (via Catmull-Rom)

Draws a wave along a path using a Catmull-Rom curve.

## Signature

```text
cetz.decorations.wave(
  target: drawable,
  close:  auto | bool   = auto,
  name:   none | string = none,
  ..style: style,
)
```

## Parameters

- **`target`** — the path to decorate.
- **`close`** — close the resulting path.
- **`name`** — element name.
- **`segments`** / **`segment-length`** *(style)* — number / length of
  phases.
- **`amplitude`** *(style)* — perpendicular height of the wave.
- **`tension`** *(style, float, default 0.5)* — Catmull-Rom curve tension.
  See [`catmull`](../../../shapes/14-catmull.md).
- **`start`** / **`stop`** *(style, ratio)* — clipping percentages along
  the path.

## Styling

- **Root:** `wave`

## Example

See [`examples/03-wave/03-wave.typ`](./examples/03-wave/03-wave.typ).
