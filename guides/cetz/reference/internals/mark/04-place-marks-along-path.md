# `mark.place-marks-along-path()` — Multi-Mark Placement

Walks a path and places marks at the positions implied by the style —
typically the start, end, and any intermediate `pos:` entries.

## Signature

```text
place-marks-along-path(ctx: dictionary, style: dictionary, transform: matrix, path: array, add-path: bool = true) -> array
```

## Parameters

- **`ctx`** — current canvas context.
- **`style`** — resolved mark style.
- **`transform`** — current transform.
- **`path`** — path segments to walk.
- **`add-path`** — if `true`, the path itself is added to the result
  alongside the marks.

## Example

See [`examples/04-place-marks-along-path/04-place-marks-along-path.typ`](./examples/04-place-marks-along-path/04-place-marks-along-path.typ).
