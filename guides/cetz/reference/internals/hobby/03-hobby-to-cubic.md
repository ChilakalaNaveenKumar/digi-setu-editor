# `hobby.hobby-to-cubic()` — Combined Open / Closed Entry Point

Dispatches to either `hobby-to-cubic-open` or `hobby-to-cubic-closed`
depending on the `close` flag — this is the function the `hobby` shape
actually calls.

## Signature

```text
hobby-to-cubic(points: array, ta: auto = auto, tb: auto = auto, rho: auto = auto, omega: auto = auto, close: bool = false) -> array
```

## Parameters

- **`points`** — points to interpolate.
- **`ta`**, **`tb`**, **`rho`**, **`omega`** — Hobby tuning parameters.
- **`close`** — `true` for a closed Hobby curve.

## Example

See [`examples/03-hobby-to-cubic/03-hobby-to-cubic.typ`](./examples/03-hobby-to-cubic/03-hobby-to-cubic.typ).
