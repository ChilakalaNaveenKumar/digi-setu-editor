# `styles.resolve()` — Resolve A Style

Resolves a style dictionary against the current style tree. It folds in
the per-element root (e.g. `circle:`), the per-call overrides, and the
"global" defaults.

## Signature

```text
resolve(dict: dictionary, root: array = (), merge: dictionary = (:), base: dictionary = (:)) -> dictionary
```

## Parameters

- **`dict`** — the current style tree (typically `ctx.style`).
- **`root`** — optional element path, e.g. `("circle",)`, used to pull a
  per-element subtree.
- **`merge`** — per-call overrides to fold on top of the resolved style.
- **`base`** — fallback values applied at the bottom of the fold stack.

## Example

See [`examples/01-resolve/01-resolve.typ`](./examples/01-resolve/01-resolve.typ).
