# `lang-fill`

The background colour of the language pill. Can be a function that takes
the language dictionary (see [`languages`](./16-languages.md)) and returns
a fill, or `none`, or a fixed paint value.

| Field | Value |
| ----- | ----- |
| Type | `none`, `color`, `gradient`, `tiling`, or `function` |
| Default | `(lang) => lang.color.lighten(80%)` |
| Contextual function | no |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
*Fixed fill:*
#codly(lang-fill: red)
```py
print('Hello, world!')
print('Goodbye, world!')
```

*Function mapping:*
#codly(lang-fill: (lang) => lang.color.lighten(40%))
```py
print('Hello, world!')
print('Goodbye, world!')
```
```

See [`examples/27-lang-fill/27-lang-fill.typ`](./examples/27-lang-fill/27-lang-fill.typ).

## Related

- [`26-lang-stroke.md`](./26-lang-stroke.md), [`16-languages.md`](./16-languages.md).
