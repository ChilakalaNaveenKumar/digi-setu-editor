# `codly-skip()` — Skip Convenience Wrapper

Convenience function for setting the [`skips`](../codly/37-skips.md)
argument of `codly`.

## Signature

```text
codly-skip(position, length) -> none
```

Two positional integers:

| Arg | Meaning |
| --- | ------- |
| `position` | the line *after* which to insert the skip (zero-indexed, like the first element of [`skips`](../codly/37-skips.md) tuples) |
| `length` | the number of source lines that the skip "swallows" (added to the displayed line numbers after the skip) |

> **Note** — Unlike the [`skips`](../codly/37-skips.md) argument of
> `codly`, `codly-skip` takes **two separate positional arguments** —
> not a single `(position, length)` tuple. To insert *several* skips
> with one call, use `codly(skips: ((p1, l1), (p2, l2), ...))` instead.

## Example

```typst
#codly-skip(4, 32)
```py
def fib(n):
  if n <= 1:
    return n
  return fib(n - 1) + fib(n - 2)
fib(25)
```
```

Equivalent to `#codly(skips: ((4, 32),))`.

See [`examples/02-codly-skip/02-codly-skip.typ`](./examples/02-codly-skip/02-codly-skip.typ).

## Related

- [`../codly/37-skips.md`](../codly/37-skips.md),
  [`../codly/38-skip-line.md`](../codly/38-skip-line.md),
  [`../codly/39-skip-number.md`](../codly/39-skip-number.md).
