# `interp-inv(values, value, spacing)`

Inverse of [`interp`](01-interp.md). Given a `length` value, return
the fractional `index` such that `interp(values, index) == value`.

## Signature

```typst
interp-inv(
  values:  array,    // array of lengths (the same as interp)
  value:   length,
  spacing: length default 0pt,
) -> float
```

## Why Fletcher needs it

This is the engine behind `xy-to-uv`: given a physical x-coordinate,
find which fractional column it sits in. The function is monotonic
(it assumes `values` is sorted) so the lookup is unambiguous.

## Example

```typst
#fletcher.interp-inv((0pt, 1cm, 3cm), 2cm)  // → 1.5
```

See [`examples/02-interp-inv/02-interp-inv.typ`](examples/02-interp-inv/02-interp-inv.typ).

## Pitfalls

- For values *outside* the array's range, the helper extrapolates
  using `spacing`; pass `spacing: 0pt` (the default) and you'll get
  the same `index` for any `value < values.first()` (a clamp).
- The result is unitless (a `float`).

## Related

- Forward: [`interp`](01-interp.md)
- Used by: [`xy-to-uv`](../coords/02-xy-to-uv.md)
