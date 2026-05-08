# `codly-range()` — Range Convenience Wrapper

Convenience function for setting the [`range`](../codly/13-range.md)
argument of `codly`. If you provide more than one range, sets
[`ranges`](../codly/14-ranges.md) instead.

## Signature

```text
codly-range(start, end: ..., ..extra-ranges) -> none
```

- A single positional `start` (and optional named `end:`) sets `range:
  (start, end)`.
- More positional arguments after that — each itself a `(start, end)`
  tuple — turn into `ranges:`.

## Examples

### Single range

```typst
#codly-range(2, end: 2)
```py
def fib(n):
  if n <= 1:
    return n
  return fib(n - 1) + fib(n - 2)
fib(25)
```
```

Renders only line 2.

### Multiple ranges

```typst
#codly-range(2, end: 2, (4, 5))
```py
def fib(n):
  if n <= 1:
    return n
  return fib(n - 1) + fib(n - 2)
fib(25)
```
```

Renders lines 2, 4, and 5.

See [`examples/03-codly-range/03-codly-range.typ`](./examples/03-codly-range/03-codly-range.typ).

## Pitfalls

- One-indexed line numbers (matches the `range` argument).
- Combine with [`smart-skip: true`](../codly/15-smart-skip.md) to render
  ellipses between disjoint ranges.

## Related

- [`../codly/13-range.md`](../codly/13-range.md),
  [`../codly/14-ranges.md`](../codly/14-ranges.md),
  [`../codly/15-smart-skip.md`](../codly/15-smart-skip.md).
