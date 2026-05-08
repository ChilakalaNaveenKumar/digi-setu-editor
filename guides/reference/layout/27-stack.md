# `stack(dir: ttb, spacing: none, ..children)` — arrange items along an axis

Lays out items along a single axis with optional spacing.

## Parameters

| Param      | Type                              | Default  | Notes                                                                |
| ---------- | --------------------------------- | -------- | -------------------------------------------------------------------- |
| `dir`      | direction                          | `ttb`     | Stacking direction. One of `ltr`, `rtl`, `ttb`, `btt`.              |
| `spacing`  | `none` / relative / fraction       | `none`    | Default gap between adjacent items.                                  |
| `children` | content / relative / fraction      | required  | Items. Length / fraction values become **explicit gaps**.            |

## Inline gaps

Pass a length or fraction as one of the children to insert an explicit gap there:

```typst
#stack(
  dir: ltr,
  rect(width: 30pt),
  1fr,             // takes all remaining space
  rect(width: 30pt),
  20pt,            // fixed 20pt gap
  rect(width: 30pt),
)
```

## Direction methods (recap)

| Call           | Returns         |
| -------------- | --------------- |
| `ttb.start()`  | `top`           |
| `ttb.end()`    | `bottom`        |
| `ttb.axis()`   | `"vertical"`    |
| `ttb.inv()`    | `btt`           |

## Stack vs grid

| Tool      | Suited for                                  |
| --------- | ------------------------------------------- |
| `stack`    | Single-axis arrangement                      |
| `grid`     | 2-D arrangement with track sizing            |

## Accessibility

Stack carries no special semantics — AT reads children in source order.

## Examples (compile-verified)

- `examples/27-stack/01-stack.typ` — vertical default, horizontal `ltr`, `rtl` reversal, mixing fixed / fractional inline gaps.

## Reference

https://typst.app/docs/reference/layout/stack/
