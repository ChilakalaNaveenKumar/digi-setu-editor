# `cetz.decorations.square()` — Square Wave

Draws a square wave along a path using a line-strip.

## Signature

```text
cetz.decorations.square(
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
- **`factor`** *(style, ratio, default 50%)* — square-wave midpoint.
- **`start`** / **`stop`** *(style, ratio)* — clipping percentages along
  the path.

## Styling

- **Root:** `squre` (note: spelling preserved from the upstream manual).

## Example

See [`examples/04-square/04-square.typ`](./examples/04-square/04-square.typ).
