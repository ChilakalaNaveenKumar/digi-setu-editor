# `codly-offset()` — Offset Convenience Wrapper

Convenience function for setting the [`offset`](../codly/11-offset.md)
argument of `codly`.

## Signature

```text
codly-offset(offset: 0) -> none
```

> **Note** — `offset` is a **named** argument, not positional. Calling
> `#codly-offset(5)` raises *"unexpected argument"*; use
> `#codly-offset(offset: 5)` instead.

## Example

```typst
#codly-offset(offset: 5)
```typ
Hello, world!
```
```

Equivalent to `#codly(offset: 5)`. Renders the single line as line 6.

See [`examples/04-codly-offset/04-codly-offset.typ`](./examples/04-codly-offset/04-codly-offset.typ).

## Related

- [`../codly/11-offset.md`](../codly/11-offset.md),
  [`../codly/12-offset-from.md`](../codly/12-offset-from.md).
