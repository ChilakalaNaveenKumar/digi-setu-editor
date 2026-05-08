# `codly-disable()` — Globally Disable Codly

Disables Codly globally. Equivalent to `codly(enabled: false)`.

## Signature

```text
codly-disable() -> none
```

## Example

```typst
*Enabled codly*
```typ
= Example
*Hello, World!*
```

*Disabled codly*
#codly-disable()
```typ
= Example
*Hello, World!*
```
```

See [`examples/09-codly-disable/09-codly-disable.typ`](./examples/09-codly-disable/09-codly-disable.typ).

## Related

- [`08-codly-enable.md`](./08-codly-enable.md) — global re-enable.
- [`06-no-codly.md`](./06-no-codly.md) — local-section disable.
- [`../codly/02-enabled.md`](../codly/02-enabled.md).
