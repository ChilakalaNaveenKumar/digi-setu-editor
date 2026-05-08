# `math.frac(num, denom, style: "vertical")` — fraction

Renders a fraction. Has a dedicated syntax shortcut: `a / b`.

## Parameters

| Param   | Type     | Default      | Notes                                                                              |
| ------- | -------- | ------------ | ---------------------------------------------------------------------------------- |
| `num`   | content  | required     | Numerator.                                                                          |
| `denom` | content  | required     | Denominator.                                                                        |
| `style` | str      | `"vertical"`  | One of `"vertical"`, `"skewed"`, `"horizontal"`.                                  |

## Syntax shortcut

| Markup        | Effect                                                       |
| ------------- | ------------------------------------------------------------ |
| `a/b`          | `frac(a, b)`                                                  |
| `(x+1)/2`      | Outer parens are *grouping only* — they get removed in `"vertical"` and `"skewed"` styles. |
| `((x+1))/2`    | Nest parens to **preserve** the parentheses in the output.  |
| `(x+1)/2` with `style: "horizontal"` | Parens are **kept** (horizontal needs them for clarity). |

## Style variants

| Style          | Output                            |
| -------------- | --------------------------------- |
| `"vertical"`    | Stacked with horizontal bar (default) |
| `"skewed"`      | `a/b` with slanted slash         |
| `"horizontal"`  | Inline `a/b` (parens retained)    |

A common pattern: keep block equations stacked but make inline ones horizontal:

```typst
#show math.equation.where(block: false): set math.frac(style: "horizontal")
```

## Examples (compile-verified)

- `examples/08-frac/01-frac.typ` — slash shorthand, all three styles, global default, inline-only horizontal via show-set.

## Reference

https://typst.app/docs/reference/math/frac/
