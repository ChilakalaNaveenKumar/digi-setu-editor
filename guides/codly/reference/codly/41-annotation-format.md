# `annotation-format`

The format of the annotation number. Can be `none` (no number) or a
function that formats the annotation number (an int) into content.

| Field | Value |
| ----- | ----- |
| Type | `none` or `function` |
| Default | `numbering.with("(1)")` |
| Contextual function | no |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
#codly(annotation-format: numbering.with("[1]"))
```

## Related

- [`40-annotations.md`](./40-annotations.md),
  [`53-reference-number-format.md`](./53-reference-number-format.md).
