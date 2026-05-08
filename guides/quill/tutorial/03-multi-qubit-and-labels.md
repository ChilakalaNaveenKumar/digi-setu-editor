# 3 — Multi-qubit gates and wire labels

This page covers two tightly-related primitives:

- `mqgate(body, n: ...)` — a gate that spans **multiple wires**.
- `lstick(body)` / `rstick(body)` — labels at the **start / end** of a wire.

## `mqgate(body, n)` — multi-wire gate

`mqgate` lays a single gate body across `n` consecutive wires starting
at the current row.

```typst
#quantum-circuit(
  1, mqgate($E_"bit"$, n: 3), 1, [\ ],
  2, [\ ],
  2,
)
```

Useful arguments:

- `n: int` — number of wires to span (default 1).
- `target: int | none` — also draw a control wire to a relative target
  (e.g. `target: -1` for a controlled multi-qubit gate).
- `wire-count: int` — number of parallel control lines (1 = quantum, 2 = classical).
- `inputs: array` / `outputs: array` — labels inside the gate for input
  / output wires.
- `pass-through: array` — let some interior wires pass through the box
  (set `fill: none` so the wires aren't covered).

Full signature: see [`reference/gates/02-mqgate.md`](../reference/gates/02-mqgate.md).

## `lstick` and `rstick` — wire labels

`lstick` puts a label at the start of a wire (no incoming wire on its
left); `rstick` puts a label at the end. Both can span multiple wires
with `n: ...` and draw a brace by default when `n > 1`:

```typst
#quantum-circuit(
  lstick($|psi〉$), 1, rstick($|psi〉$), [\ ],
  lstick($|0〉$, n: 2), 1, rstick($|0〉$, n: 2), [\ ],
  2,
)
```

The brace can be customised with `brace: "{" | "}" | "[" | "]" | "|" | none | auto`.
Pass `brace: none` to drop the brace even when `n > 1`. Pass an
explicit string to force a brace even for a single-wire stick.

## A textbook bit-flip error-correction circuit

The Quill manual's running example combines all three primitives:

```typst
#quantum-circuit(
  lstick($|psi〉$), ctrl(1), ctrl(2), mqgate($E_"bit"$, n: 3),
    ctrl(1), ctrl(2), targ(), rstick($|psi〉$), [\ ],
  lstick($|0〉$), targ(), 2, targ(), 1, ctrl(-1), 1, [\ ],
  lstick($|0〉$), 1, targ(), 2, targ(), ctrl(-1), 1
)
```

See [`examples/03-multi-qubit-and-labels/03-multi-qubit-and-labels.typ`](examples/03-multi-qubit-and-labels/03-multi-qubit-and-labels.typ).

## Pitfalls

- A gate body sitting on the **wrong wire** is a layout problem, not a
  syntax error — Quill will silently lay it out somewhere unexpected.
  Always start a fresh wire with `[\ ]`.
- For `mqgate` with `pass-through`, you must set `fill: none` or the
  pass-through wires get hidden behind the gate body.
- The default brace shows only when `n > 1`; pass an explicit
  `brace: "{"` for a single-wire brace.

## Next

[`04-wires.md`](04-wires.md) — `setwire`, classical and bundled wires.
