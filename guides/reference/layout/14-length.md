# `length` (type) — sizes and distances

Numeric type for sizes, distances, and positions.

## Units

| Unit  | Notation     | Notes                                     |
| ----- | ------------ | ----------------------------------------- |
| `pt`  | `12pt`        | Points (72pt = 1in)                       |
| `mm`  | `25mm`        | Millimeters                                |
| `cm`  | `2.54cm`      | Centimeters                                |
| `in`  | `1in`         | Inches                                     |
| `em`  | `2em`         | Relative to current font size              |

## Composition

Lengths can mix absolute units with `em`. The result is a sum:

```typst
3em + 5pt              // length whose em-part is 3 and abs-part is 5pt
```

Arithmetic: `+`, `-`, multiplication / division by `int` or `float`.

## Fields

| Field | Notes                                                                |
| ----- | -------------------------------------------------------------------- |
| `abs` | A length containing only the **absolute** component.                  |
| `em`  | The number of `em` units, as a `float`.                              |

```typst
(3em + 5pt).em           // 3.0
(3em + 5pt).abs          // 5pt (length)
```

## Methods

| Method            | Returns / Effect                                                                              |
| ----------------- | --------------------------------------------------------------------------------------------- |
| `pt()`             | Convert to a float of points. **Errors** if the length has any `em` component.                |
| `mm()`             | Convert to mm.                                                                                |
| `cm()`             | Convert to cm.                                                                                |
| `inches()`         | Convert to inches.                                                                            |
| `to-absolute()`    | Resolve `em` to absolute using the current context's font size. **Requires `context`**.        |

For lengths that mix absolute + em, drop the em first: `(3em + 5pt).abs.pt()` returns `5.0`.

## Resolving `em` requires context

Because `em` depends on the current font size, converting `2em → 24pt` only works inside a `context` block:

```typst
#set text(size: 12pt)
#context (2em).to-absolute()      // 24pt

#set text(size: 6pt)
#context (2em).to-absolute()      // 12pt
```

## Examples (compile-verified)

- `examples/14-length/01-length.typ` — literal lengths in different units, arithmetic, `.em` / `.abs` fields, conversion methods, `to-absolute()` under different font sizes.

## Reference

https://typst.app/docs/reference/layout/length/
