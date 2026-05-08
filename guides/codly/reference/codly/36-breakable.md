# `breakable`

Whether the code blocks are breakable across page and column breaks.

| Field | Value |
| ----- | ----- |
| Type | `bool` |
| Default | `true` |
| Contextual function | no |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Pitfalls

- `breakable: true` is required for [`header-repeat`](./04-header-repeat.md)
  and [`footer-repeat`](./08-footer-repeat.md) to work.
- For very tall blocks that you want to keep on one page, set
  `breakable: false` — Typst will then push the whole block to the next
  page if it doesn't fit.

## Example

```typst
#codly(breakable: false)
```py
... a long block that should not be split across pages ...
```
```

See [`examples/36-breakable/36-breakable.typ`](./examples/36-breakable/36-breakable.typ).

## Related

- [`04-header-repeat.md`](./04-header-repeat.md),
  [`08-footer-repeat.md`](./08-footer-repeat.md).
