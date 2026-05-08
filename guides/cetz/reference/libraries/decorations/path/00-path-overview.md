# Path Decorations — Overview

| Function | Page |
| -------- | ---- |
| `cetz.decorations.zigzag(target, ...)` | [`01-zigzag.md`](./01-zigzag.md) |
| `cetz.decorations.coil(target, ...)` | [`02-coil.md`](./02-coil.md) |
| `cetz.decorations.wave(target, ...)` | [`03-wave.md`](./03-wave.md) |
| `cetz.decorations.square(target, ...)` | [`04-square.md`](./04-square.md) |

Each takes a **drawable** as `target` (typically a `line(...)`) and replaces
it with a decorated rendering. Common style keys: `amplitude`,
`segments` / `segment-length`, `start`, `stop`, optional `factor`.
