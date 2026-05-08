# `scale(factor: 100%, x: ..., y: ..., origin: center + horizon, reflow: false, body)`

Scales content. **Negative** scale on an axis mirrors. Like `rotate`, layout is unaffected unless `reflow: true`.

## Parameters

| Param    | Type                       | Default              | Notes                                                       |
| -------- | -------------------------- | -------------------- | ----------------------------------------------------------- |
| `factor` | `auto` / length / ratio     | `100%`                | Positional shorthand for both axes.                         |
| `x`      | `auto` / length / ratio     | `100%`                | Horizontal scale factor. Negative = mirror.                 |
| `y`      | `auto` / length / ratio     | `100%`                | Vertical scale factor. Negative = mirror.                   |
| `origin` | alignment                    | `center + horizon`    | Pivot.                                                      |
| `reflow` | bool                         | `false`               | Adjust layout to scaled bounding box.                       |
| `body`   | content                      | required              | Content to scale.                                            |

## Mirroring

```typst
#scale(x: -100%)[This is mirrored.]
#scale(y: -100%)[Upside-down.]
#scale(x: -100%, y: -100%)[Both axes — like rotate(180deg) but mirrored.]
```

## Per-axis vs symmetric

| Form                            | Effect                                  |
| ------------------------------- | --------------------------------------- |
| `scale(50%)[X]`                 | Both axes 50%.                          |
| `scale(x: 50%)[X]`              | Only horizontal 50%; vertical stays.   |
| `scale(x: 200%, y: 100%)[X]`     | Stretched horizontally.                 |

## `reflow` matters

Without `reflow: true`, surrounding content acts as if the body were unscaled — useful for visual tweaks that shouldn't disturb layout. With `reflow: true`, the layout box is updated.

## Examples (compile-verified)

- `examples/25-scale/01-scale.typ` — mirroring, symmetric `factor`, per-axis `x`/`y`, origin alignment.

## Reference

https://typst.app/docs/reference/layout/scale/
