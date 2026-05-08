# `get-ctx()` — Read the Canvas Context

An advanced element that lets you read the current canvas context via a
callback and return elements based on it. Used for resolving anchors to
vectors, reading the transform matrix, or making decisions based on
`ctx.shared-data`.

## Signature

```text
get-ctx(
  callback: function,
)
```

The callback has the signature `(ctx) => elements`. The returned elements
are added to the canvas in-place.

## Common helpers callable inside `get-ctx`

| Helper | Purpose |
| ------ | ------- |
| `cetz.coordinate.resolve(ctx, ..coords)` | Resolve coordinate strings to `(ctx, vec, vec, …)` |
| `cetz.styles.resolve(ctx.style, root: "<elem>", merge: …)` | Compute a style dictionary |
| `cetz.util.resolve-number(ctx, n)` | Convert a number to canvas units |
| `cetz.util.measure(ctx, content)` | Measure content size in canvas coords |

## Pitfalls

- Returning `none` is allowed.
- The function must not have side-effects on `ctx`; for that, use
  [`set-ctx`](./08-set-ctx.md).

## Example

See [`examples/09-get-ctx/09-get-ctx.typ`](./examples/09-get-ctx/09-get-ctx.typ).
