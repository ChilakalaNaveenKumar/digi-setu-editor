# `lang-outset`

The X and Y outset of the language pill, applied as a `dx` and `dy`
during the `place` operation. **Applies in every case**, whether or not
you're using the default language-block formatter. The default value is
chosen to get rid of the inset applied to each line.

| Field | Value |
| ----- | ----- |
| Type | `dictionary` |
| Default | `(x: 0.32em, y: 0em)` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
#codly(lang-outset: (x: -10pt, y: 5pt))
```py
print('Hello, world!')
print('Goodbye, world!')
```
```

See [`examples/24-lang-outset/24-lang-outset.typ`](./examples/24-lang-outset/24-lang-outset.typ).

## Related

- [`23-lang-inset.md`](./23-lang-inset.md), [`28-lang-format.md`](./28-lang-format.md).
