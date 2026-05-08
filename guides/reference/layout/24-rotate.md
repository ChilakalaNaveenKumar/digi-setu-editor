# `rotate(angle, origin: center + horizon, reflow: false, body)` — rotate content

Rotates content by an angle. By default the **layout doesn't change** — siblings act as if the content stayed at its original orientation, which can cause visual overlap. Set `reflow: true` to make the layout reflect the new bounding box.

## Parameters

| Param    | Type        | Default              | Notes                                                              |
| -------- | ----------- | -------------------- | ------------------------------------------------------------------ |
| `angle`  | angle        | `0deg`                | Rotation amount (clockwise). Accepts `deg` or `rad`.               |
| `origin` | alignment    | `center + horizon`    | Pivot point of the rotation.                                       |
| `reflow` | bool         | `false`               | If `true`, surrounding layout adjusts to the rotated bounding box.  |
| `body`   | content      | required              | Content to rotate.                                                  |

## `reflow` matters

```typst
A #rotate(90deg)[B] C            // 'B' rotates but layout treats it as original 'B'
A #rotate(90deg, reflow: true)[B] C   // surrounding layout knows 'B' is taller now
```

Use `reflow: true` when the rotated content needs to **occupy** its rotated footprint (e.g., 90° text in a table cell).

## Origin

The pivot defaults to the center of the bounding box. Move it with any [alignment](./02-alignment.md):

```typst
#rotate(30deg, origin: top + left)[X]      // pivot at top-left corner
#rotate(30deg, origin: bottom + right)[X]   // pivot at bottom-right corner
```

## Examples (compile-verified)

- `examples/24-rotate/01-rotate.typ` — sweep through angles, origin alignment variants, `reflow: false` vs `true`, radian input.

## Reference

https://typst.app/docs/reference/layout/rotate/
