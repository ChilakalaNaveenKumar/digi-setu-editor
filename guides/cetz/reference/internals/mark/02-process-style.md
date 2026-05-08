# `mark.process-style()` — Resolve Mark Style

Resolves a mark style against the current context — applying the style
root inheritance, expanding shorthand, and computing per-mark sizing.

## Signature

```text
process-style(ctx: dictionary, style: dictionary, root: str, path-length: float) -> dictionary
```

## Parameters

- **`ctx`** — current canvas context.
- **`style`** — input style dictionary.
- **`root`** — style root (e.g. `"mark"`).
- **`path-length`** — length of the path the mark will be placed on.

## Example

See [`examples/02-process-style/02-process-style.typ`](./examples/02-process-style/02-process-style.typ).
