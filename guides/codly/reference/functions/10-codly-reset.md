# `codly-reset()` — Reset to Defaults

Resets all Codly settings to their default values. Useful when you want
to undo any cumulative `codly(...)` calls and start fresh.

## Signature

```text
codly-reset() -> none
```

## Example

```typst
*Global state with red color*
#codly(fill: red)
```typ
= Example
*Hello, World!*
```

*Reset it*
#codly-reset()
```typ
= Example
*Hello, World!*
```
```

The first block is filled red; the second is back to the default
unfilled look.

See [`examples/10-codly-reset/10-codly-reset.typ`](./examples/10-codly-reset/10-codly-reset.typ).

## Pitfalls

- A bare `codly()` call (no arguments) does **not** reset — it leaves
  every sticky setting in place. Use `codly-reset()` for an actual
  reset.

## Related

- [`../codly/01-codly.md`](../codly/01-codly.md).
