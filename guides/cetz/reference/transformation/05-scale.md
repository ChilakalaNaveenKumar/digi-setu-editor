# `scale()` — Scale the Coordinate System

Scales the transformation matrix by the given factor(s).

## Signature

```text
scale(
  ..args: float | ratio,
  origin: none | coordinate = none,
)
```

## Parameters

- **`..args`** — either a single positional factor (uniform), or any
  combination of `x:`, `y:`, `z:` named factors. A `ratio` of `100%` equals
  a value of `1`.
- **`origin`** — point to scale around. Default `(0, 0, 0)`.

## Pitfalls

- **Content does not scale automatically.** Text inside `content(...)` keeps
  its drawn font size — use the `auto-scale: true` style on `content` if you
  want it to scale with the canvas.

## Example

See [`examples/05-scale/05-scale.typ`](./examples/05-scale/05-scale.typ).
