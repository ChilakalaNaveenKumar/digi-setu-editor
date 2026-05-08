# `radius`

The radius of the border of the code block. See Typst's `block.radius`
for more information.

| Field | Value |
| ----- | ----- |
| Type | `length` |
| Default | `0.32em` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
*Default radius:*
```py
print('Hello, world!')
```

*Overriden radius:*
#codly(radius: 2em)
```py
print('Hello, world!')
```

*Zero radius:*
#codly(radius: 0pt)
```py
print('Hello, world!')
```
```

See [`examples/18-radius/18-radius.typ`](./examples/18-radius/18-radius.typ).

## Related

- [`19-inset.md`](./19-inset.md), [`22-stroke.md`](./22-stroke.md),
  [`25-lang-radius.md`](./25-lang-radius.md),
  [`45-highlight-radius.md`](./45-highlight-radius.md).
