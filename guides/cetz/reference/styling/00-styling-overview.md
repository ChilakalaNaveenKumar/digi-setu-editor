# Styling — Overview

The styling sub-module provides the helpers that change *inherited* styling
inside a canvas scope, plus the registry for custom marks.

| Function | Purpose | Page |
| -------- | ------- | ---- |
| `set-style(..key: value)` | Set arbitrary styling for the current scope. | [`01-set-style.md`](./01-set-style.md) |
| `fill(<paint>)` | Shorthand for `set-style(fill: <paint>)`. | [`02-fill.md`](./02-fill.md) |
| `stroke(<stroke>)` | Shorthand for `set-style(stroke: <stroke>)`. | [`03-stroke.md`](./03-stroke.md) |
| `register-mark(symbol, body)` | Define a new arrowhead/marker. | [`04-register-mark.md`](./04-register-mark.md) |

For the conceptual treatment (per-call vs inherited, style roots, folding
rules, marks), read [`../../tutorial/05-styling.md`](../../tutorial/05-styling.md).
