# Functions — Overview

Helper functions exported by the `codly` package, in addition to
[`codly(...)`](../codly/01-codly.md) itself.

| Function | Purpose | Page |
| -------- | ------- | ---- |
| `codly-init` | The show rule that activates Codly. Apply once near the top of every document with `#show: codly-init`. | [`01-codly-init.md`](./01-codly-init.md) |
| `codly-skip(...)` | Convenience wrapper for the [`skips`](../codly/37-skips.md) argument of `codly`. | [`02-codly-skip.md`](./02-codly-skip.md) |
| `codly-range(start, end: ..., ...)` | Convenience wrapper for the [`range`](../codly/13-range.md) (or [`ranges`](../codly/14-ranges.md), if more than one) argument. | [`03-codly-range.md`](./03-codly-range.md) |
| `codly-offset(offset)` | Convenience wrapper for the [`offset`](../codly/11-offset.md) argument. | [`04-codly-offset.md`](./04-codly-offset.md) |
| `local(..., body)` | Override Codly settings for a single block / section without leaking the change to the rest of the document. | [`05-local.md`](./05-local.md) |
| `no-codly[body]` | `local(enabled: false, body)`. | [`06-no-codly.md`](./06-no-codly.md) |
| `yes-codly[body]` | `local(enabled: true, body)`. | [`07-yes-codly.md`](./07-yes-codly.md) |
| `codly-enable()` | Globally turn Codly on. Equivalent to `codly(enabled: true)`. | [`08-codly-enable.md`](./08-codly-enable.md) |
| `codly-disable()` | Globally turn Codly off. Equivalent to `codly(enabled: false)`. | [`09-codly-disable.md`](./09-codly-disable.md) |
| `codly-reset()` | Reset every Codly setting to its default value. | [`10-codly-reset.md`](./10-codly-reset.md) |

## Pattern

```typst
#import "@preview/codly:1.3.0": *
#show: codly-init   // ← required exactly once

#codly-range(2, end: 5)
```py
... only lines 2-5 are shown ...
```

#no-codly[
  ```typ
  ... and this single block is rendered without Codly ...
  ```
]
```
