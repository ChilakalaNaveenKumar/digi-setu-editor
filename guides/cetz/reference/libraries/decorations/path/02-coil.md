# `cetz.decorations.coil()` — Stretched Coil / Loop Spring

Draws a stretched coil (loop spring) along a path.

## Signature

```text
cetz.decorations.coil(
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
  windings.
- **`amplitude`** *(style)* — perpendicular height of the coil.
- **`factor`** *(style, ratio)* — how far each loop extends past its
  base length to form a curl.
- **`start`** / **`stop`** *(style, ratio)* — clipping percentages along
  the path.

## Styling

- **Root:** `coil`

## Example

See [`examples/02-coil/02-coil.typ`](./examples/02-coil/02-coil.typ).
