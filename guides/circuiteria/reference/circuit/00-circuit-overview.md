# Circuit — Overview

The single drawing-envelope module. Everything Circuiteria does happens
*inside* a `circuit({ ... })` block.

| Function | Purpose | Page |
| -------- | ------- | ---- |
| `circuit(body, length)` | Drawing envelope. Sets up a CeTZ canvas configured for circuit work and exposes `element`, `wire`, `gates`, `util` to the body. | [`01-circuit.md`](./01-circuit.md) |

> `circuit` is also re-exported at the package root, so
> `circuiteria.circuit(...)` and `circuiteria.circuit.circuit(...)` are
> equivalent.

## Pattern

```typst
#import "@preview/circuiteria:0.2.0"

#circuiteria.circuit({
  import circuiteria: *
  // element / wire / gates / util are now in scope
})
```

For the conceptual treatment (why import inside the body, the
`<id>-port-<port-id>` anchor convention, coordinate forms) see
[`../../tutorial/01-getting-started.md`](../../tutorial/01-getting-started.md).
