# `highlight-stroke`

The stroke *transformer* of the [highlights](./44-highlights.md): a
function that takes the highlight's `color` and returns a stroke. Can
also be a fixed stroke value.

| Field | Value |
| ----- | ----- |
| Type | `stroke` or `function` |
| Default | `(color) => 0.5pt + color` |
| Contextual function | no |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
// Thicker highlight border
#codly(highlight-stroke: (color) => 1pt + color)
```

## Related

- [`44-highlights.md`](./44-highlights.md),
  [`46-highlight-fill.md`](./46-highlight-fill.md).
