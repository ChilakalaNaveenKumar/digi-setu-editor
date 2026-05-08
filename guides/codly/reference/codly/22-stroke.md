# `stroke`

The stroke that surrounds the whole code block.

| Field | Value |
| ----- | ----- |
| Type | `none` or `stroke` |
| Default | `1pt + luma(240)` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
*Default stroke:*
```py
print('Hello, world!')
```

*No stroke:*
#codly(stroke: none)
```py
print('Hello, world!')
```

*Overriden stroke:*
#codly(stroke: 1pt + blue)
```py
print('Hello, world!')
```
```

See [`examples/22-stroke/22-stroke.typ`](./examples/22-stroke/22-stroke.typ).

## Related

- [`18-radius.md`](./18-radius.md), [`20-fill.md`](./20-fill.md).
