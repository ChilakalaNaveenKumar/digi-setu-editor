# `meter()` — measurement

Draws a measurement symbol (the rounded "speedometer" shape) on the
wire. Meters can stand alone, connect to a classical bit on another
wire, span multiple qubits, or carry a label.

## Signature

```typst
meter(
  ..body: any,
  target:      none | int = none,
  n:           int        = 1,
  x,           y,
  wire-count:  int        = 2,
  wire-stroke: auto | stroke = auto,
  label:       label-shape = none,
  fill,
  radius,
)
```

## Variants

| Form | Result |
| ---- | ------ |
| `meter()` | Plain measurement on the wire. |
| `meter(target: 1, label: $X$)` | Drops down to the next wire (a classical bit) and labels the result `X`. |
| `meter(n: 2)` | Spans two qubits. |
| `meter[$P_1$ #meter-symbol]` | Custom body — combines text with the meter glyph. |

## Examples

```typst
// Stand-alone meter on a single wire.
#quantum-circuit(1, meter(), 1)

// Meter that drops a classical wire to qubit + 1.
#quantum-circuit(
  1, meter(target: 1, label: $X$), 1, [\ ],
  setwire(2), 3,
)

// Two-qubit meter.
#quantum-circuit(
  1, meter(n: 2), 1, [\ ], 2,
)
```

See [`examples/03-meter/03-meter.typ`](examples/03-meter/03-meter.typ).

## Custom-body meter (basis subscript)

The `meter-symbol` glyph can be combined with arbitrary content for
custom labels:

```typst
#let basis-meter(basis) = meter[
  #place(super(baseline: -0.4em, basis))
  #meter-symbol
]

#quantum-circuit(1, basis-meter[X], 1)
```

## Pitfalls

- A `target: n` meter draws a *classical* wire (default
  `wire-count: 2`) to qubit n wires below. To get a quantum wire,
  set `wire-count: 1`.
- The `n: k` argument widens the meter shape; combine with `wires: k`
  on the circuit to keep enough rows visible.
- `label: $X$` lands at the **default position** (top). Use the full
  label dictionary to reposition.

## Related

- Multi-qubit gates: [`mqgate`](02-mqgate.md)
- Wire styles: [`setwire`](../decorations/05-setwire.md)
