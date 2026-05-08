# `highlight-inset`

The inset of the highlight blocks. Can also be a dictionary with the
same keys as Typst's built-in `block.inset`.

| Field | Value |
| ----- | ----- |
| Type | `length` or `dictionary` |
| Default | `0.32em` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example: aligning highlighted and non-highlighted lines

> If alignment between highlighted and non-highlighted lines is critical
> for your use case (e.g. presentations), set the *horizontal* inset to
> zero (or close to zero) to maintain alignment between the lines.

```typst
#codly(
  highlight-inset: (x: 0pt, y: 0.32em),
  highlights: ((line: 2, start: 0),),
)
```kotlin
private val n = 0
private val n = 0
```
```

See [`examples/48-highlight-inset/48-highlight-inset.typ`](./examples/48-highlight-inset/48-highlight-inset.typ).

## Related

- [`44-highlights.md`](./44-highlights.md), [`19-inset.md`](./19-inset.md),
  [`49-highlight-outset.md`](./49-highlight-outset.md).
