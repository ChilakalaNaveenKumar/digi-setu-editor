# `cetz.angle.right-angle()` — Right Angle Decorator

Draws a right-angle "square" between rays `a` and `b` sharing the common
origin `origin`.

## Signature

```text
cetz.angle.right-angle(
  origin: coordinate,
  a:      coordinate,
  b:      coordinate,
  label:  none | content = none,
  name:   none | str = none,
  ..style: style,
)
```

## Parameters

- **`origin`** — vertex.
- **`a`**, **`b`** — coordinates on the two rays.
- **`label`** — content placed at the `label` anchor.
- **`name`** — element name.
- **`..style`** — style key-value pairs (same set as
  [`cetz.angle.angle`](./01-angle.md)).

## Styling

Same as [`cetz.angle.angle`](./01-angle.md).

## Anchors

Same as [`cetz.angle.angle`](./01-angle.md).

## Example

See [`examples/02-right-angle/02-right-angle.typ`](./examples/02-right-angle/02-right-angle.typ).
