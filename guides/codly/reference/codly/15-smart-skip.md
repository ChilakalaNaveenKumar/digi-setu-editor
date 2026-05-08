# `smart-skip`

Whether to automatically insert a `skips` entry between ranges of
displayed values. Ranges must be discontinuous for a skip to be added.
The skip will be the size of the discontinuity.

It can also be a dictionary with the keys:

| Key | Meaning |
| --- | ------- |
| `first` | whether to include a skip if the start of the block is outside of the ranges |
| `last`  | whether to include a skip if the end of the code block is outside of the ranges |
| `rest`  | whether to include a skip for unspecified values and/or in the middle of the code block |

You can specify one or more of these keys; if `rest` is not specified,
it defaults to `none`.

| Field | Value |
| ----- | ----- |
| Type | `bool` or `dictionary` |
| Default | `false` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

> **Experimental** — Report issues at https://github.com/Dherse/codly.

## Examples

### Boolean

```typst
#codly(
  smart-skip: true,
  ranges: ((2, 2), (4, 4)),
)
```py
def fib(n):
  if n <= 1:
    return n
  return fib(n - 1) + fib(n - 2)
fib(25)
```
```

### Dictionary (only middle skips)

```typst
#codly(
  smart-skip: (first: false, last: false, rest: true),
  ranges: ((2, 2), (4, 4)),
)
```
```

See [`examples/15-smart-skip/15-smart-skip.typ`](./examples/15-smart-skip/15-smart-skip.typ).

## Related

- [`13-range.md`](./13-range.md), [`14-ranges.md`](./14-ranges.md),
  [`37-skips.md`](./37-skips.md),
  [`38-skip-line.md`](./38-skip-line.md),
  [`39-skip-number.md`](./39-skip-number.md).
