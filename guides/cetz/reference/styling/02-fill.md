# `fill()` — Shorthand for `set-style(fill: …)`

Sets the current fill style for the rest of the containing scope.

## Signature

```text
fill(
  fill: paint,
)
```

## Parameters

- **`fill`** — `paint`. A color, gradient, tiling, or `none`.

## Equivalent to

```typst
set-style(fill: <fill>)
```

## See also

- [`set-style`](./01-set-style.md) for the general form.
- [`stroke`](./03-stroke.md) for the stroke equivalent.

## Example

See [`examples/02-fill/02-fill.typ`](./examples/02-fill/02-fill.typ).
