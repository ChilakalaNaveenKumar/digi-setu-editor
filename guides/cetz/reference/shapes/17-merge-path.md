# `merge-path()` — Concatenate Paths Into One

Merges two or more paths by concatenating their elements end-to-end. Anchors
and per-element styling are *not* preserved. Where a sub-path doesn't start
where the previous one ended, CeTZ inserts a straight line between them so
the result is one continuous path.

## Signature

```text
merge-path(
  body:           elements,
  join:           bool      = false,
  ignore-marks:   bool      = false,
  ignore-hidden:  bool      = false,
  close:          bool      = false,
  name:           none | str = none,
  ..style: style,
)
```

## Parameters

- **`body`** — elements whose paths to merge.
- **`join`** — when `true`, connect all sub-paths with straight lines.
- **`close`** — close the merged path with a straight line back to the
  start.
- **`ignore-marks`** — drop marks from the input elements before merging.
- **`ignore-hidden`** — when `true`, skip elements wrapped in [`hide`](../grouping/01-hide.md).
- **`name`** — element name.

## Anchors

- `centroid` — same conditions as [`compound-path`](./16-compound-path.md).
- Path anchors of the merged result.

## Pitfalls

- Pay attention to the **direction** each child path is drawn — a reversed
  segment will produce an unexpected joining line.
- Hidden child elements are dropped (per the `ignore-hidden` flag); use
  `[hide](../grouping/01-hide.md)` deliberately when you want construction
  geometry inside `merge-path`.

## Example

See [`examples/17-merge-path/17-merge-path.typ`](./examples/17-merge-path/17-merge-path.typ).

## Related

- [`compound-path`](./16-compound-path.md) — keep sub-paths separate (for
  fill-rule holes) instead of concatenating
- [`drawable.path`](../internals/drawable/04-path.md) — the underlying
  drawable
- [`path-util.normalize`](../internals/path-util/12-normalize.md) — the
  normaliser CeTZ uses to make paths uniform before merging
