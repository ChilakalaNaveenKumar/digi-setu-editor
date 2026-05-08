# `no-codly[body]` — Disable Codly Locally

A convenience function equivalent to `local(enabled: false, body)`.
Renders the wrapped block(s) **without** any Codly formatting.

## Signature

```text
no-codly(body) -> content
```

## Example

```typst
*Enabled codly*
```typ
= Example
*Hello, World!*
```

*Disabled codly*
#no-codly[
  ```typ
  = Example
  *Hello, World!*
  ```
]
```

The first block gets the Codly look; the second renders as a plain Typst
raw block.

See [`examples/06-no-codly/06-no-codly.typ`](./examples/06-no-codly/06-no-codly.typ).

## Related

- [`07-yes-codly.md`](./07-yes-codly.md) — re-enable for one section.
- [`05-local.md`](./05-local.md) — general per-section override.
- [`../codly/02-enabled.md`](../codly/02-enabled.md) — the underlying
  argument.
- [`09-codly-disable.md`](./09-codly-disable.md) — *global* disable.
