# `default-color`

The default colour to use for language pills. Used when a language is not
defined in the [`languages`](./16-languages.md) argument. Also note that
it is only used when [`lang-format`](./28-lang-format.md) is `auto` or
when you reference it from a custom formatter (the `color` named argument
that Codly passes in).

| Field | Value |
| ----- | ----- |
| Type | `color`, `gradient`, or `tiling` |
| Default | `rgb("#283593")` (dark indigo) |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
*Default color:*
```py
print('Hello, world!')
```
*Overriden default color:*
#codly(default-color: orange)
```py
print('Hello, world!')
```
```

See [`examples/17-default-color/17-default-color.typ`](./examples/17-default-color/17-default-color.typ).

## Related

- [`16-languages.md`](./16-languages.md),
  [`26-lang-stroke.md`](./26-lang-stroke.md),
  [`27-lang-fill.md`](./27-lang-fill.md).
