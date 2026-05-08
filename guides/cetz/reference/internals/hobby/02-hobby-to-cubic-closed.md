# `hobby.hobby-to-cubic-closed()` — Closed Hobby Curve → Cubics

Same as [`hobby-to-cubic-open`](./01-hobby-to-cubic-open.md) but treats
the curve as closed — the last segment loops back to the first point and
the tangents are computed cyclically.

## Signature

```text
hobby-to-cubic-closed(points: array, ta: auto = auto, tb: auto = auto, rho: auto = auto) -> array
```

## Parameters

- **`points`** — points the closed curve passes through.
- **`ta`**, **`tb`**, **`rho`** — tangent / tension overrides; defaults
  produce a canonical Hobby curve.

## Example

See [`examples/02-hobby-to-cubic-closed/02-hobby-to-cubic-closed.typ`](./examples/02-hobby-to-cubic-closed/02-hobby-to-cubic-closed.typ).
