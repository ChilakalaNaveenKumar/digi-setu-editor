# `inset`

Inset of the code lines, that is the distance between the border and the
code lines. It can also be a dictionary with the same keys as the Typst
built-in `block.inset`.

| Field | Value |
| ----- | ----- |
| Type | `length` or `dictionary` |
| Default | `0.32em` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Examples

### Single length

```typst
#codly(inset: 1em)
```py
print('Hello, world!')
```
```

### Dictionary

```typst
#codly(inset: (x: 0.32em, y: 0.1em))
```py
print('Hello, world!')
```
```

See [`examples/19-inset/19-inset.typ`](./examples/19-inset/19-inset.typ).

## Related

- [`18-radius.md`](./18-radius.md), [`23-lang-inset.md`](./23-lang-inset.md),
  [`48-highlight-inset.md`](./48-highlight-inset.md).
