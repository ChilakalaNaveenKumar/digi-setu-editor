# `math.cancel(body, length: ..., inverted: false, cross: false, angle: auto, stroke: 0.5pt)`

Draws a diagonal line over a piece of an equation — common in algebra to show that a factor cancels.

## Parameters

| Param      | Type                                | Default        | Notes                                                                              |
| ---------- | ----------------------------------- | -------------- | ---------------------------------------------------------------------------------- |
| `body`     | content                              | required       | The content to cancel.                                                             |
| `length`   | relative                             | `100% + 3pt`    | Line length, relative to the box diagonal. `100%` covers the diagonal exactly.    |
| `inverted` | bool                                 | `false`         | Flip along the Y axis (line from top-left to bottom-right).                        |
| `cross`    | bool                                 | `false`         | Draw two crossed lines (overrides `inverted`).                                     |
| `angle`    | `auto` / angle / fn(angle) → angle  | `auto`          | Rotation w.r.t. the Y axis. Function form receives the auto angle.                 |
| `stroke`   | length / color / stroke spec        | `0.5pt`         | Standard stroke spec — supports paint, thickness, dash, etc.                       |

## Examples (compile-verified)

- `examples/04-cancel/01-cancel.typ` — basic cancellation, `length`, `inverted`, `cross`, `angle` (numeric and function), custom dashed colored stroke.

## Reference

https://typst.app/docs/reference/math/cancel/
