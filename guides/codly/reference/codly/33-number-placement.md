# `number-placement`

Sets the placement of the line numbers, either `"inside"` (the default
gutter inside the block border) or `"outside"` (the gutter floats outside
the block).

| Field | Value |
| ----- | ----- |
| Type | `str` |
| Default | `"inside"` |
| Contextual function | no |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
*Line number outside of the block:*
#codly(number-placement: "outside")
```py
print('Hello, world!')
print('Goodbye, world!')
```

*Line number inside of the block:*
#codly(number-placement: "inside")
```py
print('Hello, world!')
print('Goodbye, world!')
```
```

See [`examples/33-number-placement/33-number-placement.typ`](./examples/33-number-placement/33-number-placement.typ).

## Related

- [`31-number-format.md`](./31-number-format.md),
  [`32-number-align.md`](./32-number-align.md).
