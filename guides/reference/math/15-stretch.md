# `math.stretch(body, size: 100% + 0pt)` — stretch a glyph

Stretches a stretchable glyph to a target size — most commonly used as the **base** of an attachment so that the base widens to fit its top/bottom labels (a "wide arrow", a long equals).

## Parameters

| Param  | Type     | Default        | Notes                                                          |
| ------ | -------- | -------------- | -------------------------------------------------------------- |
| `body` | content  | required       | The glyph to stretch.                                           |
| `size` | relative  | `100% + 0pt`    | Size relative to the maximum of the glyph and its attachments.  |

## What can be stretched?

Only glyphs marked stretchable in the math font. In practice that covers:

- arrows (`->`, `<-`, `<->`, `=>`, etc.)
- relations (`=`, `~`, `≈`)
- brackets and parens (`(`, `[`, `\{`, `|`)
- harpoons

Letters and most symbols cannot stretch.

## Common pattern: wide labeled arrow

```typst
$ H stretch(=)^"define" U + p V $

$ f : X stretch(->>, size: #150%)_"surjective" Y $
```

Without `stretch()`, the arrow stays narrow and the label looks oversized.

## Examples (compile-verified)

- `examples/15-stretch/01-stretch.typ` — wide arrows, harpoon, stretched bracket, comparison with non-stretched base.

## Reference

https://typst.app/docs/reference/math/stretch/
