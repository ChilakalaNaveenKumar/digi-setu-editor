# `zebra-fill`

Background colour of the code lines when zebra-striped. If set to `none`,
no zebra-striping is applied.

| Field | Value |
| ----- | ----- |
| Type | `none`, `color`, `gradient`, or `tiling` |
| Default | `luma(240)` (very light grey) |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
*Default zebra:*
```py
print('Hello, world!')
print('Hello, world!')
```

*No zebra:*
#codly(zebra-fill: none)
```py
print('Hello, world!')
print('Hello, world!')
```

*Overriden zebra:*
#codly(zebra-fill: gradient.linear(..color.map.flare))
```py
print('Hello, world!')
```
```

See [`examples/21-zebra-fill/21-zebra-fill.typ`](./examples/21-zebra-fill/21-zebra-fill.typ).

## Related

- [`20-fill.md`](./20-fill.md).
