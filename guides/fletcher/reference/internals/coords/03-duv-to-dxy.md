# `duv-to-dxy(grid, uv, duv)` — uv tangent → xy tangent

The Jacobian of [`uv-to-xy`](01-uv-to-xy.md). Converts a *small
displacement* (or velocity) in elastic coords into the corresponding
displacement in absolute coords, evaluated at a base point `uv`.

## Signature

```typst
duv-to-dxy(
  grid: dict,
  uv:   (float, float),   // base point in uv
  duv:  (float, float),   // displacement in uv
) -> (length, length)
```

## Why it exists

Elastic coords are **non-linear** — the cell at `(0, 0)` may be wider
than the cell at `(1, 0)` because they hold different-size labels.
Therefore "1 unit right in uv" is *not* a constant length in xy.
`duv-to-dxy` answers: at this `uv`, how big is `duv`?

The implementation uses balanced finite differences.

## Example

```typst
let dxy = fletcher.duv-to-dxy(grid, (0.5, 0), (0.1, 0))
// dxy is the physical equivalent of "0.1 elastic units right at (0.5, 0)"
```

See [`examples/03-duv-to-dxy/03-duv-to-dxy.typ`](examples/03-duv-to-dxy/03-duv-to-dxy.typ).

## Pitfalls

- For very large `duv`, the finite-difference approximation gets
  inaccurate — break the displacement into smaller steps if precision
  matters.
- Returning two `length` values, `dxy` *cannot* be used directly as a
  CeTZ angle / polar coord; convert via `vector` arithmetic.

## Related

- Inverse: [`dxy-to-duv`](04-dxy-to-duv.md)
- Point version: [`uv-to-xy`](01-uv-to-xy.md)
