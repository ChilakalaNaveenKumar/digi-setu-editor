# 6 — Labels (everywhere)

Every gate, decoration, and group in Quill accepts a `label:` argument
with a uniform shape. Once you understand it, you can label gates,
control wires, slices, and gategroups the same way.

## The label shape

A label can be:

| Form | Effect |
| ---- | ------ |
| `none` | No label (default). |
| string / content | Plain label at the *default position*. |
| dictionary | Labelled with custom position and offset. |
| array of dictionaries | Multiple labels on the same element. |

The dictionary keys are:

| Key | Type | Meaning |
| --- | ---- | ------- |
| `content` | content / string | The label body (required). |
| `pos` | 2D alignment (`top + left`, `bottom`, …) | Where the label sits. |
| `dx` | length / ratio / relative | Horizontal offset from `pos`. |
| `dy` | length / ratio / relative | Vertical offset from `pos`. |

For plain gates the default position is `top`. For control wires
(`mqgate`, `ctrl`, `swap`) it is `right`. For `phase` gates it is
`top + right`. Override `pos:` to move it anywhere.

## A single string label

```typst
#quantum-circuit(
  1, gate($H$, label: "Hadamard"), 1
)
```

## A custom-position label

```typst
#quantum-circuit(
  1, gate($H$, label: (content: "Hadamard", pos: bottom, dy: 0pt)), 1
)
```

## Multiple labels around the same gate

Pass an array of label dictionaries:

```typst
#quantum-circuit(
  1, gate(hide($H$), label: (
    (content: "lt", pos: left + top),
    (content: "t",  pos: top),
    (content: "rt", pos: right + top),
    (content: "l",  pos: left),
    (content: "c",  pos: center),
    (content: "r",  pos: right),
    (content: "lb", pos: left + bottom),
    (content: "b",  pos: bottom),
    (content: "rb", pos: right + bottom),
  )), 1
)
```

## Labelling a control wire

`mqgate`, `ctrl` and `swap` accept a separate `wire-label:` argument
(same shape as `label`) for the *vertical* control wire:

```typst
#quantum-circuit(
  1, ctrl(1, wire-label: $phi$), 2,
    swap(1, wire-label: (
      content: rotate(-90deg, smallcaps("swap")),
      pos: left, dx: 0pt
    )), 1, [\ ], 10pt,
  1, ctrl(), 2, swap(), 1,
)
```

See [`examples/06-labels/06-labels.typ`](examples/06-labels/06-labels.typ).

## Pitfalls

- `pos: bottom` only **moves** the label; it does not change the
  alignment relative to the gate centre. Adjust `dx` / `dy` to nudge
  individual labels for tight layouts.
- A non-`auto` value for `wire-label`'s `pos` is interpreted relative
  to the *control wire*, not the gate.
- Long multi-label arrays force the gate cell to grow — if the layout
  jitters, set a `width:` on the gate.

## Next

[`07-gate-placement.md`](07-gate-placement.md) — manual `x:` / `y:`
placement.
