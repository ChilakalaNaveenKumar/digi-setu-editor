# Gates — Overview

The gates module ships ready-made logic-gate shapes (the classic IEEE
"distinctive" symbols). All gate functions share a common parameter
family centred on `gate(...)`.

| Function | Symbol | Page |
| -------- | ------ | ---- |
| `gate(...)` | Generic gate (you provide the `draw-shape`). | [`01-gate.md`](./01-gate.md) |
| `gate-and(...)` | AND gate (D-shape). | [`02-gate-and.md`](./02-gate-and.md) |
| `gate-nand(...)` | NAND gate (D-shape with bubble). | [`03-gate-nand.md`](./03-gate-nand.md) |
| `gate-buf(...)` | Buffer (triangle). | [`04-gate-buf.md`](./04-gate-buf.md) |
| `gate-not(...)` | NOT gate / inverter (triangle with bubble). | [`05-gate-not.md`](./05-gate-not.md) |
| `gate-or(...)` | OR gate (curved-back shape). | [`06-gate-or.md`](./06-gate-or.md) |
| `gate-nor(...)` | NOR gate (OR-shape with bubble). | [`07-gate-nor.md`](./07-gate-nor.md) |
| `gate-xor(...)` | XOR gate (OR-shape with extra back-curve). | [`08-gate-xor.md`](./08-gate-xor.md) |
| `gate-xnor(...)` | XNOR gate (XOR-shape with bubble). | [`09-gate-xnor.md`](./09-gate-xnor.md) |

> Every `gate-*` function is **also** available under `element.gate-*`
> — the manual is consistent that `element.gate-and(...)` and
> `gates.gate-and(...)` produce identical output.

## Common parameter family

Every gate takes the same arguments — see [`01-gate.md`](./01-gate.md)
for the full descriptions:

```text
draw-shape:       function          = default-draw-shape
x:                number | dictionary
y:                number | dictionary
w:                number
h:                number
inputs:           int               = 2
fill:             none | color      = none
stroke:           stroke            = black + 1pt
id:               str               = ""
inverted:         str | array       = ()      // "all" or array of port ids
inverted-radius:  number            = 0.1
debug:            dictionary        = (ports: false)
```

## Built-in ports

For every gate, the input port ids are `in0`, `in1`, …, `in<inputs-1>`,
and the output is `out`. Anchors are therefore:

- `<id>-port-in0`, `<id>-port-in1`, …, `<id>-port-in<inputs-1>` (west)
- `<id>-port-out` (east)

`gate-buf` and `gate-not` ignore `inputs` (they always have one input).

## Pitfalls

- The `inverted: "all"` shortcut adds the bubble dot to every port —
  including the *output*, so combining `inverted: "all"` with `gate-and`
  visually produces a NAND-with-inverted-inputs (an OR by De Morgan).
  This matches the manual's example.
- `inverted` accepts either the string literal `"all"` or an array of
  port-id strings (e.g. `("in0",)`). It does **not** accept the bare
  port id without the array wrapper.
- `inputs` is silently ignored on `gate-buf` and `gate-not`.

## Reproducing the manual snippets

Each `gate-*.md` includes the same snippet shape the manual uses:

```text
gates.gate-<name>(x: 0, y: 0, w: 1.5, h: 1.5)
gates.gate-<name>(x: 3, y: 0, w: 1.5, h: 1.5, inverted: "all")
```

The compilable wrapped form is in
`./examples/<NN-gate-name>/<NN-gate-name>.typ`.
