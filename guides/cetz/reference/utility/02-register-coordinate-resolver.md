# `register-coordinate-resolver()` — Custom Coordinate Resolution

Pushes a custom coordinate resolver onto the chain. The resolver gets called
for every coordinate before the built-ins; multiple resolvers run in
**reverse registration order**, then CeTZ's defaults run last.

The resolver is **scoped** to the current context (canvas / group / scope).

## Signature

```text
register-coordinate-resolver(
  resolver: function,
)
```

The resolver must have the signature `(context, coordinate) => coordinate`
and must return a valid coordinate (or panic).

## Use case

Custom coordinate keys for log scaling, polar-with-units, custom node
references in a graph library, …

```typst
register-coordinate-resolver((ctx, c) => {
  if type(c) == dictionary and "log" in c {
    c = c.log.map(n => calc.log(n, base: 10))
  }
  return c
})
circle((log: (10, 1e-6)), radius: .25)
```

## Pitfalls

- Resolvers run on **every** coordinate, including ones the built-ins would
  already understand. Always early-return for keys you don't handle.
- Throwing inside the resolver bubbles up as a canvas-time panic.

## Example

See [`examples/02-register-coordinate-resolver/02-register-coordinate-resolver.typ`](./examples/02-register-coordinate-resolver/02-register-coordinate-resolver.typ).

## Related

- [`internals/coordinate`](../internals/coordinate/00-coordinate-overview.md) —
  [`coordinate.resolve`](../internals/coordinate/02-resolve.md) is what
  ultimately calls your resolver, and
  [`coordinate.resolve-system`](../internals/coordinate/01-resolve-system.md)
  is what classifies a value into a coordinate kind
- Tutorial: [Coordinates](../../tutorial/03-coordinates.md) — every
  built-in form your resolver competes with
- [Types — `coordinate`](../../types/00-types-overview.md)
