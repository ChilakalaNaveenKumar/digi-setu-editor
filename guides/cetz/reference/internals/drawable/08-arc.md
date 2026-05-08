# `drawable.arc()` — Arc Drawable

Constructs an arc drawable. The `arc` shape feeds it.

## Signature

```text
arc(
  x: float, y: float, z: float,
  start: angle, stop: angle,
  rx: float, ry: float,
  mode: "OPEN" | "CLOSE" | "PIE" = "OPEN",
  fill: color | none = none,
  stroke: stroke | none = none,
) -> drawable
```

## Parameters

- **`x`**, **`y`**, **`z`** — centre coordinates.
- **`start`**, **`stop`** — sweep angles.
- **`rx`**, **`ry`** — radii along X and Y.
- **`mode`** — open (no closing chord), closed (chord across), or pie
  (close back to centre).
- **`fill`**, **`stroke`** — render options.

## Example

See [`examples/08-arc/08-arc.typ`](./examples/08-arc/08-arc.typ).
