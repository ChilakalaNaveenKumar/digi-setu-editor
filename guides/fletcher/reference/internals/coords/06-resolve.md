# `resolve(ctx, update, ..coordinates)` — uv-aware coord resolver

`fletcher.resolve` is a thin wrapper around `cetz.coordinate.resolve`
that *also* understands Fletcher's `uv` coordinates. Use it when you
build custom drawing helpers that should accept either coordinate
system.

## Signature

```typst
resolve(
  ctx: dict,            // CeTZ context (provided to draw functions)
  update: bool,         // update the previous coord (CeTZ semantics)
  ..coordinates,        // any number of coordinates
) -> array
```

Each coordinate may be:

- a regular CeTZ coordinate (point, named, polar, …);
- a Fletcher `uv` coordinate `(u, v)` — automatically converted using
  the diagram's grid (taken from `ctx.shared-state.grid`).

The return value matches `cetz.coordinate.resolve`: the resolved 3D
points (`(x, y, z)`).

## Example

```typst
fletcher.cetz.draw.get-ctx(ctx => {
  let pts = fletcher.resolve(ctx, true, (0, 0), (uv: (1, 0)))
  fletcher.cetz.draw.line(..pts)
})
```

See [`examples/06-resolve/06-resolve.typ`](examples/06-resolve/06-resolve.typ).

## Pitfalls

- If `ctx` doesn't contain a Fletcher grid (e.g. you're outside a
  diagram's `render:` callback), passing a `uv` coord yields
  `(float.nan, …)` instead of an error — guard your call site.
- `update: true` mutates `ctx.prev`; pass `false` for read-only resolution.

## Related

- [`uv-to-xy`](01-uv-to-xy.md) — the underlying conversion.
- CeTZ docs for `cetz.coordinate.resolve` for the full coord grammar.
