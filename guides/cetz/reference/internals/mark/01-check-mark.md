# `mark.check-mark()` — Validate Mark Style

Validates a mark-style dictionary — checking that the requested symbol
exists, that the dimensions and offsets are sensible, etc. Returns the
validated style or panics if invalid.

## Signature

```text
check-mark(style: dictionary) -> dictionary
```

## Parameters

- **`style`** — a mark style dictionary (anything you would put under the
  `mark:` style root).

## Example

See [`examples/01-check-mark/01-check-mark.typ`](./examples/01-check-mark/01-check-mark.typ).
