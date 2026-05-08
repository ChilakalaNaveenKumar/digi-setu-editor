# 4 — All about wires

Quill generalises the `qcircuit` distinction between quantum, classical
and bundled wires into a single `setwire(count, ...)` command.

## `setwire(count, stroke, wire-distance)`

```typst
setwire(count: int, stroke: auto | none | stroke, wire-distance: length)
```

- `count: 0` — *no wire* (transparent).
- `count: 1` — single line (quantum wire).
- `count: 2` — two parallel lines (classical wire).
- `count: 3+` — bundle of `n` lines.

`setwire(...)` produces no cell and may be inserted anywhere on the
wire — every following item uses the new wire style. The wire setting
**resets at every `[\\ ]`**: a fresh row starts with the default style
again.

## Mixing quantum and classical wires

```typst
#quantum-circuit(
  1, $A$, meter(n: 1), [\ ],
  setwire(2, stroke: blue), 2, ctrl(), 2, [\ ],
  1, $X$, setwire(0), 1, lstick($|0〉$), setwire(1), $Y$,
)
```

What happens here:

- Wire 1 stays quantum, with an `A` gate and a meter.
- Wire 2 starts in classical-blue mode for the whole row.
- Wire 3 starts quantum, switches to *no wire* with `setwire(0)`,
  then a fresh `lstick($|0〉$)` makes a new state, and `setwire(1)`
  brings the wire back before the `Y` gate.

See [`examples/04-wires/04-wires.typ`](examples/04-wires/04-wires.typ).

## Bundled wires

Wire bundles use the same primitive — pass a count larger than 2.
Bundle width can be tuned per wire:

```typst
#quantum-circuit(
  setwire(4, wire-distance: 1.5pt), 1, $U$, meter()
)
```

For a *visual* bundle marker on a single wire, see
[`reference/decorations/04-nwire.md`](../reference/decorations/04-nwire.md)
(`nwire(label)` puts a slash + label on a wire to indicate it carries
*n* qubits).

## Pitfalls

- `setwire(0)` does **not** delete previously-drawn wire — it only
  affects what comes after. To "cut" a wire mid-circuit you switch to
  `setwire(0)` then back with `setwire(1)`.
- The wire setting resets at every `[\\ ]`. If you want a whole circuit
  in classical wires, set it at the start of *every* row.
- Stroke colour is independent of `quantum-circuit(wire: ...)`. A
  per-row `setwire(..., stroke: ...)` overrides the global wire stroke
  for that row only.

## Next

[`05-slices-and-groups.md`](05-slices-and-groups.md) — labelled phases
of the circuit.
