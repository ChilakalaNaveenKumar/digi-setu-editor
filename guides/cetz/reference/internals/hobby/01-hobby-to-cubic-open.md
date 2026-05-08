# `hobby.hobby-to-cubic-open()` — Open Hobby Curve → Cubics

Computes a list of cubic Bézier sections that smoothly interpolate the
input `points` via Hobby's algorithm. The returned spline does **not**
close.

## Signature

```text
hobby-to-cubic-open(points: array, ta: auto = auto, tb: auto = auto, rho: auto = auto, omega: auto = auto) -> array
```

## Parameters

- **`points`** — the points to interpolate.
- **`ta`** — start tangent direction (auto = solve from boundary
  conditions).
- **`tb`** — end tangent direction.
- **`rho`** — tension function (auto = canonical Hobby tension).
- **`omega`** — turning function (auto = canonical Hobby turning).

## Example

See [`examples/01-hobby-to-cubic-open/01-hobby-to-cubic-open.typ`](./examples/01-hobby-to-cubic-open/01-hobby-to-cubic-open.typ).
