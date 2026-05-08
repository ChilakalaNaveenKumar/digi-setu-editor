# `lang-stroke`

The stroke of the language pill. Can be a function that takes the
language dictionary (see [`languages`](./16-languages.md)) and returns a
stroke, or `none`, or a fixed stroke value.

| Field | Value |
| ----- | ----- |
| Type | `none`, `stroke`, or `function` |
| Default | `(lang) => lang.color + 0.5pt` |
| Contextual function | no |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
*Fixed stroke:*
#codly(lang-stroke: 1pt + red)
```py
print('Hello, world!')
print('Goodbye, world!')
```

*Function mapping:*
#codly(lang-stroke: (lang) => 2pt + lang.color)
```py
print('Hello, world!')
print('Goodbye, world!')
```
```

See [`examples/26-lang-stroke/26-lang-stroke.typ`](./examples/26-lang-stroke/26-lang-stroke.typ).

## Related

- [`27-lang-fill.md`](./27-lang-fill.md), [`16-languages.md`](./16-languages.md).
