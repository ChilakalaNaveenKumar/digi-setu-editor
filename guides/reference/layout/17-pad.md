# `pad(left: 0pt, top: 0pt, right: 0pt, bottom: 0pt, x: 0pt, y: 0pt, rest: 0pt, body)`

Adds spacing around content **without** wrapping it in a visual container (unlike `block(inset: ...)`).

## Parameters

| Param   | Type      | Default     | Notes                                         |
| ------- | --------- | ----------- | --------------------------------------------- |
| `left`   | relative  | `0% + 0pt`   | Padding on the left.                           |
| `top`    | relative  | `0% + 0pt`   | Padding on the top.                            |
| `right`  | relative  | `0% + 0pt`   | Padding on the right.                          |
| `bottom` | relative  | `0% + 0pt`   | Padding on the bottom.                         |
| `x`      | relative  | `0% + 0pt`   | Shorthand for `left` and `right`.             |
| `y`      | relative  | `0% + 0pt`   | Shorthand for `top` and `bottom`.             |
| `rest`   | relative  | `0% + 0pt`   | Catch-all for sides not specified above.       |
| `body`   | content   | required     | Content to pad.                                 |

## Precedence

When multiple sources can determine the same side, this order wins:

```
per-side (top/right/...) > axis (x/y) > rest
```

## Negative padding

Negative values shrink the apparent margin, allowing full-bleed effects on otherwise-margined documents:

```typst
#pad(x: -8pt, image("banner.png", width: 100%))
```

## Pad vs block(inset:)

| Tool          | Adds visual container? | Allows fill/border?  |
| ------------- | ---------------------- | -------------------- |
| `pad`          | No                     | No                   |
| `block(inset:)` | Yes                   | Yes (`fill`, `stroke`) |

Use `pad` when you only need spacing; use `block(inset:)` when you need a styled container.

## Examples (compile-verified)

- `examples/17-pad/01-pad.typ` — symmetric `x:`, per-side, `rest:` with selective override, negative padding.

## Reference

https://typst.app/docs/reference/layout/pad/
