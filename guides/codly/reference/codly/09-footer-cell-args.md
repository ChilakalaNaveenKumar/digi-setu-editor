# `footer-cell-args`

Additional arguments to be provided to the `grid.cell` containing the
footer. See [`header-cell-args`](./05-header-cell-args.md) for more
information.

| Field | Value |
| ----- | ----- |
| Type | `array`, `dictionary`, or `arguments` |
| Default | `()` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
// Centering the footer:
#codly(
  footer: [*Hello, world!*],
  footer-cell-args: (align: center,),
)
```typ
Hello, world!
```
```

See [`examples/09-footer-cell-args/09-footer-cell-args.typ`](./examples/09-footer-cell-args/09-footer-cell-args.typ).

## Related

- [`07-footer.md`](./07-footer.md), [`05-header-cell-args.md`](./05-header-cell-args.md).
