# `matrix.transform-rotate-aer()` — Azimuth/Elevation/Roll

Returns a 4×4 affine rotation built from azimuth/elevation/roll angles —
sometimes called *aer* angles, useful for camera/orbit setups.

## Signature

```text
transform-rotate-aer(azimuth: angle, elevation: angle, roll: angle = 0deg) -> matrix
```

## Parameters

- **`azimuth`** — rotation about the vertical axis (Y in CeTZ).
- **`elevation`** — rotation about the side axis.
- **`roll`** — rotation about the look direction; defaults to `0deg`.

## Pitfalls

- **Broken in cetz 0.5.0.** The implementation calls `mul-mat(...)`
  without the `matrix.` qualifier, raising an `unknown variable: mul-mat`
  error. The example file below builds the same matrix from
  `transform-rotate-y` and `transform-rotate-x` instead.

## Example

See [`examples/14-transform-rotate-aer/14-transform-rotate-aer.typ`](./examples/14-transform-rotate-aer/14-transform-rotate-aer.typ).
