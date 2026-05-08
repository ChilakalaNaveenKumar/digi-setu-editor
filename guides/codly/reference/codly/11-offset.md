# `offset`

The offset to apply to line numbers. This is purely cosmetic, only
impacting the shown line numbers in the final output.

| Field | Value |
| ----- | ----- |
| Type | `int` |
| Default | `0` |
| Contextual function | yes |
| Automatically reset | yes |
| Released in 1.3.1 | yes |

## Example

```typst
*No offset:*
```typ
Hello, world!
```

*Offset by 5:*
#codly(offset: 5)
```typ
Hello, world!
```
```

See [`examples/11-offset/11-offset.typ`](./examples/11-offset/11-offset.typ).

## Pitfalls

- Offset is **cosmetic only** — it does not change the underlying line
  *positions* used by [`highlights`](./44-highlights.md),
  [`annotations`](./40-annotations.md), or [`range`](./13-range.md).
  Those still use one-indexed source-line numbers.
- Offset **resets after each block**.

## Related

- [`12-offset-from.md`](./12-offset-from.md) — offset relative to a
  *previous* block.
- [`../functions/04-codly-offset.md`](../functions/04-codly-offset.md) —
  convenience wrapper.
