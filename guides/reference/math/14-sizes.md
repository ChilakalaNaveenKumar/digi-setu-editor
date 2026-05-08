# `math.display` / `inline` / `script` / `sscript` — forced size styles

Forces a sub-expression to render at one of the four math sizes used by Typst (mirrors LaTeX's `\displaystyle`, `\textstyle`, `\scriptstyle`, `\scriptscriptstyle`). Useful when you want a fraction or sum to render large/small in a place where Typst would auto-pick the other size.

## Functions

| Function          | Size                         | Default `cramped` |
| ----------------- | ---------------------------- | ----------------- |
| `display(body)`    | Normal block-equation size   | `false`            |
| `inline(body)`     | Normal inline-equation size  | `false`            |
| `script(body)`     | Sub/superscript size         | `true`             |
| `sscript(body)`    | Second-level script size     | `true`             |

All four take a `cramped` named arg (bool). `cramped: true` constrains exponent height, mirroring how real scripts are typeset (lower x-height for tightness).

## Common use

```typst
// Force a big sum inside an inline equation.
This formula reduces to $display(sum_i x_i / 2)$ as N grows.

// Force a small inline-style fraction inside a block equation
// (avoids the towering 3-line look).
$ a = inline(p / q) + b $
```

## Examples (compile-verified)

- `examples/14-sizes/01-sizes.typ` — `display`, `inline`, `script`, `sscript` all demoed side-by-side.

## Reference

https://typst.app/docs/reference/math/sizes/
