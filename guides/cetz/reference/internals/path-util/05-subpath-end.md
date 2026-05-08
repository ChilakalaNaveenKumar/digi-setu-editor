# `path-util.subpath-end()` — End Of A Subpath

Returns the end point of a subpath. By default a closed subpath returns
its origin (because semantically the path ends back where it started); if
you want the *last drawn point*, pass `ignore-close-flag: true`.

## Signature

```text
subpath-end(subpath: subpath, ignore-close-flag: bool = false) -> vector
```

## Parameters

- **`subpath`** — a single subpath triple.
- **`ignore-close-flag`** — if `true`, the closure is ignored and the
  last drawn point is returned.

## Example

See [`examples/05-subpath-end/05-subpath-end.typ`](./examples/05-subpath-end/05-subpath-end.typ).
