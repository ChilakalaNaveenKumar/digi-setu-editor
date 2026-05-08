# `styles.merge()` — Fold Two Style Dictionaries

Folds the `top` style dictionary on top of the `bottom` one. Used to
implement the inheritance order

```
defaults  ⟵  set-style  ⟵  per-call args
```

## Signature

```text
merge(bottom: dictionary, top: dictionary) -> dictionary
```

## Parameters

- **`bottom`** — base values; preserved unless overridden.
- **`top`** — overriding values.

## Example

See [`examples/02-merge/02-merge.typ`](./examples/02-merge/02-merge.typ).
