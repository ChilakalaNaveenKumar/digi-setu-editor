# `header-cell-args`

Additional arguments to be provided to the `grid.cell` containing the
header. Lets you customize the header cell further.

Internally, codly wraps the content of the [`header`](./03-header.md)
argument in a `grid.cell` with these arguments. The only argument that is
always common is the `body` argument (the value of `header`) and
`colspan: 2`.

For a full description of the argument, look at the documentation of the
`grid.cell` function in Typst.

| Field | Value |
| ----- | ----- |
| Type | `array`, `dictionary`, or `arguments` |
| Default | `()` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
// Centering the header:
#codly(
  header: [*Hello, world!*],
  header-cell-args: (align: center,),
)
```typ
Hello, world!
```
```

See [`examples/05-header-cell-args/05-header-cell-args.typ`](./examples/05-header-cell-args/05-header-cell-args.typ).

## Pitfalls

- The trailing comma on a single-pair tuple matters: `(align: center,)`
  is a tuple with one item; `(align: center)` is a dictionary literal.
  Both are accepted (since the type is `array | dictionary | arguments`)
  but mixing them up can produce confusing errors elsewhere.
- Do not pass `body` or `colspan` here — Codly already controls those.

## Related

- [`03-header.md`](./03-header.md), [`09-footer-cell-args.md`](./09-footer-cell-args.md).
