# `codly-enable()` — Globally Enable Codly

Enables Codly globally. Equivalent to `codly(enabled: true)`.

## Signature

```text
codly-enable() -> none
```

## Example

```typst
*Disabled codly*
#codly-disable()
```typ
= Example
*Hello, World!*
```

#codly-enable()

*Enabled codly*
```typ
= Example
*Hello, World!*
```
```

See [`examples/08-codly-enable/08-codly-enable.typ`](./examples/08-codly-enable/08-codly-enable.typ).

## Related

- [`09-codly-disable.md`](./09-codly-disable.md) — global disable.
- [`07-yes-codly.md`](./07-yes-codly.md) — local-section re-enable.
- [`../codly/02-enabled.md`](../codly/02-enabled.md).
