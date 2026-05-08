# `intersection.line-line()` — Line × Line Intersection

Returns the intersection point of two line segments (or lines, if `ray:
true`), or `none` if they don't meet.

## Signature

```text
line-line(p1: vector, p2: vector, p3: vector, p4: vector, ray: bool = false, eps: float = 1e-6) -> vector | none
```

## Parameters

- **`p1`**, **`p2`** — first line endpoints.
- **`p3`**, **`p4`** — second line endpoints.
- **`ray`** — if `true`, treat both lines as infinite.
- **`eps`** — numerical tolerance for parallelism.

## Example

See [`examples/01-line-line/01-line-line.typ`](./examples/01-line-line/01-line-line.typ).
