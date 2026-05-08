# `fill`

The fill of the code block when not zebra-striped (i.e. the background
under odd-numbered lines, since even lines use
[`zebra-fill`](./21-zebra-fill.md)).

| Field | Value |
| ----- | ----- |
| Type | `none`, `color`, `gradient`, or `tiling` |
| Default | `none` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
*Default fill:*
```py
print('Hello, world!')
print('Hello, world!')
```

*Overriden fill:*
#codly(fill: gradient.linear(..color.map.flare))
```py
print('Hello, world!')
print('Hello, world!')
```

*No fill:*
#codly(fill: none)
```py
print('Hello, world!')
print('Hello, world!')
```
```

See [`examples/20-fill/20-fill.typ`](./examples/20-fill/20-fill.typ).

## Pitfalls

- `fill` is for the **non-zebra** rows. To kill the zebra entirely, set
  `zebra-fill: none`. To make the whole block one colour, set both `fill`
  and `zebra-fill` to the same value.

## Related

- [`21-zebra-fill.md`](./21-zebra-fill.md),
  [`22-stroke.md`](./22-stroke.md).
