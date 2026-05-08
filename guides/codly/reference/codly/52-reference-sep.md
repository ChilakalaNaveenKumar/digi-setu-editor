# `reference-sep`

The separator to use when referencing highlights and annotations. Sits
between the listing number and the line / item.

| Field | Value |
| ----- | ----- |
| Type | `str` or `content` |
| Default | `"-"` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
#codly(reference-sep: ":")
// Now @my-label:2 renders as "Listing 1:2" instead of "Listing 1-2"
```

## Related

- [`51-reference-by.md`](./51-reference-by.md),
  [`53-reference-number-format.md`](./53-reference-number-format.md),
  [`../../tutorial/02-referencing.md`](../../tutorial/02-referencing.md).
