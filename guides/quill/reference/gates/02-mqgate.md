# `mqgate()` — multi-qubit / controlled gate

A gate that spans `n` consecutive wires and/or extends a control wire
to a relative target wire. The base for all multi-wire gate primitives.

## Signature

```typst
mqgate(
  body:       content,
  n:          int    = 1,
  target:     none | int = none,
  pass-through: array  = (),
  x:          auto | int = auto,
  y:          auto | int = auto,
  fill:       auto | none | color | gradient | tiling = auto,
  stroke:     auto | stroke = auto,
  radius:     length | dictionary = 0pt,
  width:      auto | length = auto,
  box:        bool = true,
  wire-count: int = 1,
  wire-stroke: auto | stroke = auto,
  inputs:     none | array = none,
  outputs:    none | array = none,
  extent:     auto | length = auto,
  size-all-wires: none | bool = false,
  draw-function: function = draw-functions.draw-boxed-multigate,
  label:      label-shape = none,
  wire-label: label-shape = none,
  data:       any = none,
)
```

## Key arguments

- **`n`** — wires to span (`n: 3` covers three rows).
- **`target`** — *additional* control wire to a relative target (e.g.
  `target: -1` adds a control wire to the wire above).
- **`wire-count`** — control-wire line count (1 quantum, 2 classical, etc.).
- **`wire-stroke`** — stroke for the control wire.
- **`pass-through`** — list of interior wire indices that should *pass
  through* the gate body (useful when wires must visually traverse the
  gate). Set `fill: none` so they aren't covered.
- **`inputs` / `outputs`** — labels inside the gate for input / output
  wires. Each entry is a dictionary `(qubit, content, n?)` where `qubit`
  is the index (starting at 0) within the gate and `n` groups multiple
  qubits with a brace.
- **`extent`** — extra extension above the first / below the last wire
  (default matches an `X` gate).
- **`size-all-wires`** — `false` (default) sizes only first/last;
  `true` sizes every wire; `none` ignores sizing.
- **`wire-label`** — labels on the *control* wire.

## Examples

### Three-qubit error-correction box

```typst
#quantum-circuit(
  wires: 3,
  1, mqgate($E$, n: 3), 1,
)
```

> **Pitfall:** if your `mqgate` declares `n: 3` rows and the circuit
> only has one wire so far, set `wires: 3` (or add `[\ ]` row breaks) —
> otherwise compilation fails with `"A 3-qubit gate ... exceeds the
> circuit which has only 1 qubits"`.

### Pass-through inner wire

```typst
#quantum-circuit(
  wires: 4,
  1, mqgate(
    n: 4,
    fill: none,
    pass-through: (2,),
    $E$
  ), 1
)
```

### Gate with input / output labels

```typst
#quantum-circuit(
  wires: 3,
  1, mqgate($U$, n: 3, width: 5em,
    inputs: (
      (qubit: 0, n: 2, label: $x$),
      (qubit: 2, label: $y$)
    ),
    outputs: (
      (qubit: 0, n: 2, label: $x$),
      (qubit: 2, label: $y plus.o f(x)$)
    ),
  )
)
```

> **Pitfall:** Typst 0.14 deprecated `plus.circle` in favour of
> `plus.o`. Use the new symbol or compilation prints a deprecation
> warning.

See [`examples/02-mqgate/02-mqgate.typ`](examples/02-mqgate/02-mqgate.typ).

## Pitfalls

- The (relative) **first and last** wires can never be in `pass-through`.
  Only inner wires can pass through.
- For pass-through to be visible, set `fill: none` — otherwise the gate
  fill will hide the wires.
- `target: 0` is invalid; use a non-zero relative wire.
- `extent: auto` matches an `X` gate's height. For very tall gate
  bodies set an explicit length.

## Related

- Single-qubit: [`gate`](01-gate.md)
- Control symbols: [`ctrl`](09-ctrl.md), [`targ`](06-targ.md), [`swap`](08-swap.md)
- Wire labels: [tutorial 6](../../tutorial/06-labels.md)
