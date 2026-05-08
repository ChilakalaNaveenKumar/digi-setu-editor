# `lang-inset`

The inset of the language pill. This only applies if you're using the
default language-block formatter (`lang-format: auto`). It can also be a
dictionary with the same keys as Typst's built-in `block.inset`.

| Field | Value |
| ----- | ----- |
| Type | `length` or `dictionary` |
| Default | `0.32em` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
#codly(lang-inset: 5pt)
```py
print('Hello, world!')
print('Goodbye, world!')
```
```

See [`examples/23-lang-inset/23-lang-inset.typ`](./examples/23-lang-inset/23-lang-inset.typ).

## Related

- [`19-inset.md`](./19-inset.md), [`24-lang-outset.md`](./24-lang-outset.md),
  [`25-lang-radius.md`](./25-lang-radius.md),
  [`28-lang-format.md`](./28-lang-format.md).
