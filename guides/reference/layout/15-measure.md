# `measure(content, width: auto, height: auto)` — measure laid-out size

Returns the laid-out size of content as `(width, height)` lengths. **Requires context** because the result depends on font size, language, available width, etc.

## Parameters

| Param     | Type           | Default  | Notes                                                            |
| --------- | -------------- | -------- | ---------------------------------------------------------------- |
| `content` | content         | required | The content to measure.                                          |
| `width`   | `auto` / length | `auto`   | Available width. `auto` = infinite (single-line measurement).    |
| `height`  | `auto` / length | `auto`   | Available height.                                                |

Returns a dictionary `(width: length, height: length)`.

## Context required

```typst
#let label(body) = context {
  let size = measure(body)
  [(#size.width)] + body
}

#label[Hi]
#label[Welcome]
```

Without `#context`, you'll get an error: measurement depends on the current style (font size, language) which is only resolved during layout.

## Bounding the layout width

| Call                                  | Effect                                                         |
| ------------------------------------- | -------------------------------------------------------------- |
| `measure(body)`                        | Single-line measurement (treats width as infinite).             |
| `measure(body, width: 300pt)`           | Wraps content into 300pt and reports the resulting box.        |

## `measure(body, width: ...)` vs `measure(block(body, width: ...))`

These give **different** results:

```typst
#context measure(lorem(50), width: 200pt)
// Returns the dimensions the inner content takes when laid out
// in a 200pt-wide region.

#context measure(block(lorem(50), width: 200pt))
// Returns the dimensions of the BLOCK -- which has been forced
// to width: 200pt -- so width is exactly 200pt.
```

Use the **bare `width:` arg** when you want the inner content's dimensions; wrap in a `block` when you want the block's dimensions.

## Common patterns

| Goal                                 | Recipe                                                |
| ------------------------------------ | ----------------------------------------------------- |
| Decide spacing based on content size | `context { let s = measure(body); v(s.height + 2pt) }` |
| Implement a content-aware show rule  | `show heading: it => context { ...measure(it.body)... }` |
| Auto-size a custom callout box       | Combine with `block(width: measure(...).width + 2*pad)` |

## Examples (compile-verified)

- `examples/15-measure/01-measure.typ` — context-bound measurement, varying text sizes, width-bounded measurement, sized-block vs raw-content measurement.

## Reference

https://typst.app/docs/reference/layout/measure/
