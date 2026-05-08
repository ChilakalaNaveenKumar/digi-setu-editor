# `set-ctx()` — Mutate the Canvas Context

An advanced element that lets you modify the current canvas `ctx` object via
a callback. Use it to override the transform matrix, store shared state, or
hook in any custom mutation.

## Signature

```text
set-ctx(
  callback: function,
)
```

The callback has the signature `(ctx) => ctx`. Return the new context.

## Notes

- The transform matrix is **rounded** after the callback is called. This is
  to avoid floating-point drift; it should not cause practical problems.
- Use `ctx.shared-data` (a dictionary) for canvas-global state. It is **not**
  scoped by `group` or `scope` — perfect for stateful canvases (counters,
  caches, palettes).
- See [`get-ctx`](./09-get-ctx.md) to read the context.

## Pitfalls

- Manipulating `ctx.transform` directly can produce surprising effects in
  combination with the higher-level [`transformation/`](../transformation/)
  helpers; prefer those when possible.

## Example

See [`examples/08-set-ctx/08-set-ctx.typ`](./examples/08-set-ctx/08-set-ctx.typ).
