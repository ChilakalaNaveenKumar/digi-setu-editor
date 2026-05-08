# `stroke()` — Shorthand for `set-style(stroke: …)`

Sets the current stroke style for the rest of the containing scope.

## Signature

```text
stroke(
  stroke: stroke,
)
```

## Parameters

- **`stroke`** — `stroke`. A `length`, `color`, `length + color`,
  `dictionary`, or full `stroke(...)` object. Pass `none` to disable.

## Equivalent to

```typst
set-style(stroke: <stroke>)
```

## See also

- [`set-style`](./01-set-style.md), [`fill`](./02-fill.md).

## Example

See [`examples/03-stroke/03-stroke.typ`](./examples/03-stroke/03-stroke.typ).
