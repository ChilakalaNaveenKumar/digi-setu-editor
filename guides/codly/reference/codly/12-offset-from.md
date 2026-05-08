# `offset-from`

The offset to apply to line numbers, relative to **another code block**.
This is useful when you want to match line numbers between two code
blocks. The current block's line numbers will continue from the other
block, with the specified offset.

This is done by giving a label to the parent raw block, and then setting
that label as the `offset-from` on the second code block.

| Field | Value |
| ----- | ----- |
| Type | `none` or `label` |
| Default | `none` |
| Contextual function | yes |
| Automatically reset | yes |
| Released in 1.3.1 | yes |

> **Info** — The offset obtained from the other code block is **added
> to** the value of [`offset`](./11-offset.md) (so they compose).
>
> **Warning** — Important: this feature works with any offset set on the
> other code block, including `offset-from`, but may give unexpected
> results if both code blocks have `offset-from` set to each other or if
> the preceding code block has `range` or `skips` set.
>
> **Experimental** — Report issues at
> https://github.com/Dherse/codly.

## Example

```typst
```py
def fib(n):
  if n <= 1:
    return n
  return fib(n - 1) + fib(n - 2)
``` <fib-fn>

*Will continue at line 5*
#codly(offset-from: <fib-fn>)
```py
fib(25)
```
```

See [`examples/12-offset-from/12-offset-from.typ`](./examples/12-offset-from/12-offset-from.typ).

## Pitfalls

- The label must be on the **raw block** (after the closing backticks),
  not on a surrounding figure.
- Combining `offset-from` with `range` or `skips` on the *parent* block
  may produce surprising line numbers.
- `offset-from` resets after each block, like `offset`.

## Related

- [`11-offset.md`](./11-offset.md), [`13-range.md`](./13-range.md),
  [`37-skips.md`](./37-skips.md).
