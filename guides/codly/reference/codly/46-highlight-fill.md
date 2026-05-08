# `highlight-fill`

The fill *transformer* of the [highlights](./44-highlights.md): a
function that takes the highlight's `color` and returns a fill (paint).

| Field | Value |
| ----- | ----- |
| Type | `function` |
| Default | `(color) => color.lighten(80%)` |
| Contextual function | no |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
// More opaque highlights
#codly(highlight-fill: (color) => color.lighten(20%))
```

## Related

- [`44-highlights.md`](./44-highlights.md),
  [`47-highlight-stroke.md`](./47-highlight-stroke.md).
