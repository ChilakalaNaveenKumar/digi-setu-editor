# `interp(values, index, spacing)`

Linearly interpolate a fractional `index` across an array of
`length`-typed `values`. Outside `[0, len(values)-1]` it falls back to
linear extrapolation with gradient `spacing`.

## Signature

```typst
interp(
  values:  array,        // array of lengths
  index:   int | float,
  spacing: length default 0pt,  // gradient for out-of-bounds extrapolation
) -> length
```

## Why Fletcher needs it

The elastic grid is essentially a piecewise-linear function from
`uv` indices to `xy` lengths. `uv-to-xy` is implemented on top of
`interp`; reading the source of `interp` is the fastest way to
understand how Fletcher reasons about *fractional* row/column
positions.

## Example

```typst
#import "@preview/fletcher:0.5.8" as fletcher
#fletcher.interp((0pt, 1cm, 3cm), 1.5)   // → 2cm
#fletcher.interp((0pt, 1cm, 3cm), 3.0, spacing: 1cm)  // → 4cm
```

See [`examples/01-interp/01-interp.typ`](examples/01-interp/01-interp.typ).

## Pitfalls

- `index` must be a number, not a `length`.
- `values` must be an array of `length` (mixing `length` and `int`
  raises an error).

## Related

- Inverse: [`interp-inv`](02-interp-inv.md)
- Used by: [`uv-to-xy`](../coords/01-uv-to-xy.md)
