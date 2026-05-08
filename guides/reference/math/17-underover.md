# `math.underline` / `overline` / `underbrace` / `overbrace` / `underbracket` / `overbracket` / `underparen` / `overparen` / `undershell` / `overshell`

Group of functions that draw a horizontal **delimiter or line** above or below an expression. The brace/bracket/paren/shell variants additionally accept an **annotation** that sits on the open side.

> **Note:** these `underline` / `overline` are the **math** versions. The text-mode `underline()` / `overline()` (different module) draws a line under/over running text. Inside `$...$`, the math versions take precedence.

## Functions and signatures

| Function                           | Renders                                        |
| ---------------------------------- | ---------------------------------------------- |
| `underline(body)`                   | Body with a horizontal line under it.          |
| `overline(body)`                    | Body with a horizontal line over it.           |
| `underbrace(body, annotation?)`     | Body with `︸` underneath; optional label below. |
| `overbrace(body, annotation?)`      | Body with `︷` above; optional label above.     |
| `underbracket(body, annotation?)`   | Body with `⎵` underneath; optional label below. |
| `overbracket(body, annotation?)`    | Body with `⎴` above; optional label above.     |
| `underparen(body, annotation?)`     | Body with `⏝` underneath; optional label below. |
| `overparen(body, annotation?)`      | Body with `⏜` above; optional label above.     |
| `undershell(body, annotation?)`     | Body with tortoise-shell `⏡` underneath.        |
| `overshell(body, annotation?)`      | Body with tortoise-shell `⏠` above.             |

`annotation` defaults to `none`. When set, the brace/bracket/paren/shell delimiter remains and the annotation is placed in the natural slot.

## Common pattern

```typst
$ underbrace(a_1 + a_2 + dots + a_n, "n terms") = sum_(i=1)^n a_i $
```

## Examples (compile-verified)

- `examples/17-underover/01-under-over.typ` — plain `underline`/`overline`, all six brace/bracket/paren/shell variants with annotations.

## Reference

https://typst.app/docs/reference/math/underover/
