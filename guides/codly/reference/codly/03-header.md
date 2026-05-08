# `header`

An optional header to display above the code block. It can be optionally
repeated on all subsequent pages with the
[`header-repeat`](./04-header-repeat.md) argument. Additional
customisations are available with
[`header-cell-args`](./05-header-cell-args.md) and
[`header-transform`](./06-header-transform.md).

| Field | Value |
| ----- | ----- |
| Type | `content` or `none` |
| Default | `none` |
| Contextual function | yes |
| Automatically reset | yes |
| Released in 1.3.1 | yes |

## Example

```typst
#codly(header: [*Hello, world!*])
```typ
Hello, world!
```
```

See [`examples/03-header/03-header.typ`](./examples/03-header/03-header.typ).

## Pitfalls

- The header **resets after each block**. Set it again before the next
  block if you want it to repeat.
- The header is wrapped in a `grid.cell` with `colspan: 2` so it spans
  the entire block width. To override other `grid.cell` args use
  [`header-cell-args`](./05-header-cell-args.md).

## Related

- [`07-footer.md`](./07-footer.md) — the bottom counterpart.
- [`04-header-repeat.md`](./04-header-repeat.md),
  [`05-header-cell-args.md`](./05-header-cell-args.md),
  [`06-header-transform.md`](./06-header-transform.md).
