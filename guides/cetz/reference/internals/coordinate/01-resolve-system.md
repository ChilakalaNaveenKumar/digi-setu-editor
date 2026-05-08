# `coordinate.resolve-system()` — Detect Coordinate System

Inspects a value and returns the name of the coordinate system it belongs
to — `"xyz"`, `"polar"`, `"anchor"`, `"relative"`, `"barycentric"`,
`"function"`, `"lerp"`, `"tangent"`, `"perpendicular"`, or
`"project-point-on-line"`.

This is what `coordinate.resolve()` uses internally to dispatch.

## Signature

```text
resolve-system(ctx: dictionary, c: any) -> str
```

## Parameters

- **`ctx`** — the canvas context (passed through from `set-ctx`/`get-ctx`).
- **`c`** — the coordinate value to classify.

## Example

See [`examples/01-resolve-system/01-resolve-system.typ`](./examples/01-resolve-system/01-resolve-system.typ).
