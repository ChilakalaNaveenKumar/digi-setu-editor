# `cetz.angle.angle()` — Angle Between Two Rays

Draws an angle (counter-clockwise by default) between rays `a` and `b`
sharing the common origin `origin`.

## Signature

```text
cetz.angle.angle(
  origin: coordinate,
  a:      coordinate,
  b:      coordinate,
  direction: string             = "ccw",
  label:     none | content | function = none,
  name:      none | str = none,
  ..style: style,
)
```

## Parameters

- **`origin`** — vertex of the angle.
- **`a`** — coordinate on the first ray.
- **`b`** — coordinate on the second ray.
- **`direction`** — `"ccw"` (counter-clockwise, default), `"cw"`,
  `"near"` (inner angle), `"far"` (outer angle).
- **`label`** — content to draw at the `label` anchor. Pass a function
  `(angle) => content` to label by computed angle.
- **`name`** — element name.
- **`..style`** — style key-value pairs.
- **`radius`** *(style)* — `number | ratio`. Arc radius. Ratios are relative
  to the smaller of `|origin → a|` and `|origin → b|`.
- **`label-radius`** *(style)* — radius of the label's origin (relative to
  `radius` if a ratio).

## Styling

- **Root:** `angle`

## Anchors

| Anchor | Position |
| ------ | -------- |
| `a` | point on ray `a` (the input) |
| `b` | point on ray `b` (the input) |
| `origin` | the angle's vertex |
| `label` | label centre |
| `start` | arc start |
| `end` | arc end |

## Example

See [`examples/01-angle/01-angle.typ`](./examples/01-angle/01-angle.typ).
