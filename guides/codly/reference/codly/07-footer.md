# `footer`

An optional footer to display below the code block. See
[`header`](./03-header.md) for more information.

| Field | Value |
| ----- | ----- |
| Type | `content` or `none` |
| Default | `none` |
| Contextual function | yes |
| Automatically reset | yes |
| Released in 1.3.1 | yes |

## Example

```typst
#codly(footer: [*Hello, world!*])
```typ
Hello, world!
```
```

See [`examples/07-footer/07-footer.typ`](./examples/07-footer/07-footer.typ).

## Pitfalls

- Like `header`, the footer **resets after each block**. Re-set it for
  each block where you want it.
- The footer is also wrapped in a `grid.cell` with `colspan: 2`. Override
  other `grid.cell` args with [`09-footer-cell-args.md`](./09-footer-cell-args.md).

## Related

- [`03-header.md`](./03-header.md),
  [`08-footer-repeat.md`](./08-footer-repeat.md),
  [`09-footer-cell-args.md`](./09-footer-cell-args.md),
  [`10-footer-transform.md`](./10-footer-transform.md).
