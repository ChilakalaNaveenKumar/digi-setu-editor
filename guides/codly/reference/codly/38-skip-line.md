# `skip-line`

Sets the content with which the *line code* column is filled when a
skip is encountered.

| Field | Value |
| ----- | ----- |
| Type | `content` or `none` |
| Default | `align(center)[ ... ]` (a centred ellipsis) |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
#codly(
  skips: ((4, 32),),
  skip-line: align(center, emoji.face.shock),
)
```py
def fib(n):
  if n <= 1:
    return n
  return fib(n - 1) + fib(n - 2)
fib(25)
```
```

See [`examples/38-skip-line/38-skip-line.typ`](./examples/38-skip-line/38-skip-line.typ).

## Related

- [`37-skips.md`](./37-skips.md), [`39-skip-number.md`](./39-skip-number.md).
