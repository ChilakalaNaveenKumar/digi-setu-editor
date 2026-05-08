# `footer-transform`

Function that transforms the footer into arbitrary content to be stored
in the `grid.cell`. Can be seen as a show-rule for the footer. See
[`header-transform`](./06-header-transform.md) for more information.

| Field | Value |
| ----- | ----- |
| Type | `function` |
| Default | `(x) => x` |
| Contextual function | no |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
// Making the footer bold and blue:
#codly(
  footer: [Hello, world!],
  footer-transform: (x) => {
    set text(fill: blue)
    strong(x)
  },
)
```typ
Hello, world!
```
```

See [`examples/10-footer-transform/10-footer-transform.typ`](./examples/10-footer-transform/10-footer-transform.typ).

## Related

- [`07-footer.md`](./07-footer.md),
  [`06-header-transform.md`](./06-header-transform.md).
