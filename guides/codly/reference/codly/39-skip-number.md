# `skip-number`

Sets the content with which the *line number* column is filled when a
skip is encountered. If line numbers are disabled (via
[`number-format: none`](./31-number-format.md)), this has no effect.

| Field | Value |
| ----- | ----- |
| Type | `content` or `none` |
| Default | `[ ... ]` (an ellipsis) |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
#codly(
  skips: ((4, 32),),
  skip-number: align(center, emoji.face.shock),
)
```py
def fib(n):
  if n <= 1:
    return n
  return fib(n - 1) + fib(n - 2)
fib(25)
```
```

See [`examples/39-skip-number/39-skip-number.typ`](./examples/39-skip-number/39-skip-number.typ).

## Related

- [`37-skips.md`](./37-skips.md), [`38-skip-line.md`](./38-skip-line.md).
