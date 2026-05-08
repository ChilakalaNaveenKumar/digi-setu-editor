# `enabled`

Whether codly is enabled or not. If it is disabled, the code block will
be displayed as a normal code block, without any additional
codly-specific formatting. This is useful if you want to disable codly
for a specific block.

| Field | Value |
| ----- | ----- |
| Type | `bool` |
| Default | `true` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
*Enabled = true*:
#codly(enabled: true)
```typ
Hello, world!
```

*Enabled = false*:
#codly(enabled: false)
```typ
Hello, world!
```
```

See [`examples/02-enabled/02-enabled.typ`](./examples/02-enabled/02-enabled.typ).

## Related

- [`../functions/06-no-codly.md`](../functions/06-no-codly.md) — local
  one-section equivalent (`local(enabled: false, body)`).
- [`../functions/07-yes-codly.md`](../functions/07-yes-codly.md) — local
  one-section re-enable (`local(enabled: true, body)`).
- [`../functions/08-codly-enable.md`](../functions/08-codly-enable.md),
  [`../functions/09-codly-disable.md`](../functions/09-codly-disable.md) —
  global toggles.
