# Brace Decorations — Overview

| Function | Page |
| -------- | ---- |
| `cetz.decorations.brace(start, end, ...)` | [`01-brace.md`](./01-brace.md) |
| `cetz.decorations.flat-brace(start, end, ...)` | [`02-flat-brace.md`](./02-flat-brace.md) |

Both draw a curly-bracket between two points. `flat-brace` mimics TikZ's
`decorations.pathreplacing` library and uses straight line segments —
better-looking for long, low-amplitude braces than the curve-based `brace`.
