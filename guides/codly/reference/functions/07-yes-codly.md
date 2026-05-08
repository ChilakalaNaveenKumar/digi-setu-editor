# `yes-codly[body]` — Re-enable Codly Locally

A convenience function equivalent to `local(enabled: true, body)`. Useful
when Codly is currently disabled globally and you want one section to
get the full treatment anyway.

## Signature

```text
yes-codly(body) -> content
```

## Example

```typst
*Disabled codly*
#codly(enabled: false)
```typ
= Example
*Hello, World!*
```

*Enabled codly*
#yes-codly[
  ```typ
  = Example
  *Hello, World!*
  ```
]
```

The first block renders plainly; the wrapped second block gets the Codly
look, even though the global state says "disabled".

See [`examples/07-yes-codly/07-yes-codly.typ`](./examples/07-yes-codly/07-yes-codly.typ).

## Related

- [`06-no-codly.md`](./06-no-codly.md) — local *disable*.
- [`05-local.md`](./05-local.md) — general per-section override.
- [`../codly/02-enabled.md`](../codly/02-enabled.md) — the underlying
  argument.
- [`08-codly-enable.md`](./08-codly-enable.md) — *global* enable.
