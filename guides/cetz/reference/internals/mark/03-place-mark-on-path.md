# `mark.place-mark-on-path()` — Single Mark Placement

Computes the position, direction and orientation of a single mark on a
specific point of a path — used for the `start:` and `end:` mark slots.

## Signature

```text
place-mark-on-path(ctx: dictionary, styles: dictionary, segments: array, is-end: bool = false) -> array
```

## Parameters

- **`ctx`** — current canvas context.
- **`styles`** — resolved mark style.
- **`segments`** — path segments to compute against.
- **`is-end`** — `false` for the start mark, `true` for the end mark.

## Example

See [`examples/03-place-mark-on-path/03-place-mark-on-path.typ`](./examples/03-place-mark-on-path/03-place-mark-on-path.typ).
