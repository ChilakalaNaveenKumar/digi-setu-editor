# `coordinate` — Coordinate Resolution

`cetz.coordinate` turns the user-facing coordinate forms (xyz tuples,
polar, anchor strings, relative dictionaries, function form, …) into
canonical 3D vectors that the rest of the engine can consume.

The module is exposed at `cetz.coordinate.<fn>`.

## Functions

| File | Function |
| --- | --- |
| [`01-resolve-system.md`](./01-resolve-system.md) | `resolve-system()` |
| [`02-resolve.md`](./02-resolve.md) | `resolve()` |

## Related

- Tutorial: [Coordinates](../../../tutorial/03-coordinates.md) — every
  user-facing form `resolve` accepts
- [`register-coordinate-resolver`](../../utility/02-register-coordinate-resolver.md)
  — extend `resolve` with custom forms
- [Types — `coordinate`](../../../types/00-types-overview.md)
