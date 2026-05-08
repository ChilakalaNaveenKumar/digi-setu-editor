# `set-origin()` — Move the Origin

Sets the given position as the new origin `(0, 0, 0)`.

## Signature

```text
set-origin(
  origin: coordinate,
)
```

## Parameters

- **`origin`** — the coordinate to make the new origin.

## Pitfalls

- Implemented as a translation, so subsequent `(0, 0)` references resolve to
  the new location and *all* subsequent draws are shifted.
- Inside a `group`, the origin reverts when the scope exits.

## Example

See [`examples/06-set-origin/06-set-origin.typ`](./examples/06-set-origin/06-set-origin.typ).
