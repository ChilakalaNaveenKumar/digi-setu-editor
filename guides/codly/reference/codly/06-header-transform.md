# `header-transform`

Function that transforms the header into arbitrary content to be stored
in the `grid.cell`. Can be seen as a show-rule for the header. This
allows you to perform global transformation / show-rule-like operations
on the header.

| Field | Value |
| ----- | ----- |
| Type | `function` |
| Default | `(x) => x` |
| Contextual function | no |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
// Making the header bold and blue:
#codly(
  header: [Hello, world!],
  header-transform: (x) => {
    set text(fill: blue)
    strong(x)
  },
)
```typ
Hello, world!
```
```

See [`examples/06-header-transform/06-header-transform.typ`](./examples/06-header-transform/06-header-transform.typ).

## Pitfalls

- The transform receives the *raw `header` value*. If `header` is `none`
  the transform is not called.
- Use this for *global* transforms (every block's header). For per-block
  styling, set `header:` directly to the transformed content.

## Related

- [`03-header.md`](./03-header.md),
  [`10-footer-transform.md`](./10-footer-transform.md).
