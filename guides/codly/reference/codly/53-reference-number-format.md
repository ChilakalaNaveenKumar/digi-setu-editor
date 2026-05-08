# `reference-number-format`

The format of the line-number portion of a reference. Only used when
[`reference-by`](./51-reference-by.md) is `"line"`.

| Field | Value |
| ----- | ----- |
| Type | `function` |
| Default | `numbering.with("1")` |
| Contextual function | no |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
#codly(reference-number-format: numbering.with("I"))
// @my-label:2 renders as "Listing 1-II"
```

## Related

- [`51-reference-by.md`](./51-reference-by.md),
  [`52-reference-sep.md`](./52-reference-sep.md),
  [`31-number-format.md`](./31-number-format.md),
  [`../../tutorial/02-referencing.md`](../../tutorial/02-referencing.md).
