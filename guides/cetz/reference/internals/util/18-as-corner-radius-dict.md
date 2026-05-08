# `util.as-corner-radius-dict()` — Normalize A Corner-Radius Spec

Coerces the various accepted corner-radius forms — single number, 2-tuple
`(x, y)`, 4-tuple per-corner, or dictionary — into a canonical
per-corner dictionary.

## Signature

```text
as-corner-radius-dict(ctx: dictionary, radii: any, size: vector) -> dictionary
```

## Parameters

- **`ctx`** — current canvas context.
- **`radii`** — input radius spec.
- **`size`** — the shape's `(width, height)` (used to clamp radii to
  half the shape size).

## Example

See [`examples/18-as-corner-radius-dict/18-as-corner-radius-dict.typ`](./examples/18-as-corner-radius-dict/18-as-corner-radius-dict.typ).
