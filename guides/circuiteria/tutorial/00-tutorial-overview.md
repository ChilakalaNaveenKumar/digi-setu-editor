# Circuiteria Tutorial — Overview

Read this short tutorial before diving into the per-function pages under
[`../reference/`](../reference/).

| File | Covers |
| ---- | ------ |
| [`01-getting-started.md`](./01-getting-started.md) | Installing the package, the `circuit { … }` envelope, the `import circuiteria: *` idiom, ports, the `<id>-port-<port-id>` anchor convention, connecting elements with `wire.wire(...)`. |

After this you should be comfortable navigating any function under
`../reference/`. Each function's `.md` page assumes you know:

1. The drawing happens inside `circuiteria.circuit({ import circuiteria: *; … })`.
2. Circuiteria sits on top of CeTZ, so `(x, y)` coordinates follow the CeTZ
   convention — *y grows upward* — and CeTZ functions like
   `draw.circle(...)`, `draw.line(...)`, `draw.content(...)` are still
   available inside the body, but only after an explicit
   `#import "@preview/cetz:0.3.2": draw` (the `draw` namespace is *not*
   re-exported by `import circuiteria: *`).
3. Every element you give an `id:` to exposes anchors of the form
   `<id>-port-<port-id>` (with `-port-` between, **not** a dot) plus the
   normal CeTZ compass anchors `<id>.north / .east / .south / .west /
   .center`.
4. Wires are *named*: `wire.wire("w1", (a, b))` exposes anchors like
   `w1.zig` (for zig-zag wires) or `w1.start / w1.end`.
