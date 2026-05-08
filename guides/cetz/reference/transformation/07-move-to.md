# `move-to()` — Set the Previous Coordinate

Sets the *previous coordinate* used by relative coordinates and the empty
tuple `()`. **Does not** modify the transformation matrix.

## Signature

```text
move-to(
  pt: coordinate,
)
```

## Parameters

- **`pt`** — the new "previous coordinate".

## Pitfalls

- Frequently confused with `set-origin`. `move-to` only changes what `()`
  / `(rel: …)` resolve to; the canvas origin is unchanged.

## Example

See [`examples/07-move-to/07-move-to.typ`](./examples/07-move-to/07-move-to.typ).
