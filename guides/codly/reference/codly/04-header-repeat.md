# `header-repeat`

Whether to repeat the header on each page. This is only applicable if
a [`header`](./03-header.md) is provided, if the code block is
[`breakable`](./36-breakable.md), and if it actually breaks on more than
one page. For more information see Typst's `grid.header.repeat`.

| Field | Value |
| ----- | ----- |
| Type | `bool` |
| Default | `false` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
#codly(
  header: [*Repeats on every page*],
  header-repeat: true,
  breakable: true,
)
```typ
... long code block that spans pages ...
```
```

See [`examples/04-header-repeat/04-header-repeat.typ`](./examples/04-header-repeat/04-header-repeat.typ).

## Pitfalls

- Repeating only takes effect when **all three** of the following are
  true: `header` is set, `breakable: true`, and the block actually
  breaks. A short, non-breaking block silently ignores the flag.

## Related

- [`03-header.md`](./03-header.md), [`08-footer-repeat.md`](./08-footer-repeat.md),
  [`36-breakable.md`](./36-breakable.md).
