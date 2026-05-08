# `wires` — explicit wire layout

`wires:` lets you tell Quill how many wires the circuit has (instead
of letting it infer from `[\\ ]` row breaks). Accepts:

| Value | Meaning |
| ----- | ------- |
| `auto` (default) | Inferred from `[\\ ]` and `mqgate` extents. |
| Integer (`3`) | Force exactly N wires (all single quantum lines). |
| Array (`(1, 1, 2)`) | Per-wire `setwire` count: here two quantum then one classical. |

Useful when:

- A leading `mqgate(n: 3)` would otherwise crash because the circuit
  only knows about 1 wire so far. Set `wires: 3`.
- You want a specific mixed quantum/classical layout from the start.

## Examples

```typst
// Force 3 wires from the start (no [\\ ] needed).
#quantum-circuit(
  wires: 3,
  1, mqgate($U$, n: 3), 1,
)

// Mixed: two quantum + one classical wire.
#quantum-circuit(
  wires: (1, 1, 2),
  1, $H$, 1, [\ ],
  1, $H$, 1, [\ ],
  1, ctrl(-2, wire-count: 2), 1,
)
```

See [`examples/07-wires-explicit/07-wires-explicit.typ`](examples/07-wires-explicit/07-wires-explicit.typ).

## Pitfalls

- An array `wires: (1, 1, 2)` overrides any per-row `setwire(...)` for
  the *initial* wire style; you can still call `setwire(...)` mid-row.
- `wires: 3` does not magically add row breaks — you still need `[\\ ]`
  if you want to *use* those wires for individual gates.
- Mismatched lengths (e.g. `wires: (1, 1)` with three actual wires)
  silently misalign — keep the array length equal to the number of
  rows.

## Related

- Wire styling per row: [`setwire`](../decorations/05-setwire.md)
- Auto-extending wires: [`08-fill-wires.md`](08-fill-wires.md)
