# `lstick()` — label at the start of a wire

Adds a label "sticking out" to the **left** of the first cell on the
current wire. With `n > 1` it spans multiple wires and shows a `{`
brace by default.

## Signature

```typst
lstick(
  body:   content,
  n:      int = 1,
  brace:  auto | none | str = auto,
  pad:    length = 0pt,
  label:  label-shape = none,
  x, y,
)
```

## Brace rules

| `brace` | Single wire (`n: 1`) | Multi-wire (`n > 1`) |
| ------- | -------------------- | -------------------- |
| `auto` (default) | No brace | `{` brace |
| `none` | No brace | No brace |
| `"{"`, `"}"`, `"["`, `"]"`, `"|"` | Forces that brace | Forces that brace |

## Examples

```typst
// Single-wire label.
#quantum-circuit(lstick($|0〉$), 1)

// Multi-wire brace.
#quantum-circuit(
  lstick($rho$, n: 2), 1, [\ ],
  1
)

// Forced bracket on a single wire.
#quantum-circuit(lstick($|psi〉$, brace: "["), 1)
```

See [`examples/01-lstick/01-lstick.typ`](examples/01-lstick/01-lstick.typ).

## Pitfalls

- `lstick` must be the **first** child on its wire. Putting cells
  before it leaves no room for the label and the brace will draw on
  top of those cells.
- A multi-wire `lstick(...)` reserves vertical space across the
  declared rows — those rows must actually exist (use `[\\ ]` row
  breaks).
- `pad: 4pt` adds horizontal space to the **right** of the brace, not
  to the left of the label. To shift the label leftwards, use a `dx`
  inside the `label` dictionary.

## Related

- Right-end version: [`rstick`](02-rstick.md)
- Mid-circuit text: [`midstick`](03-midstick.md)
- Tutorial walkthrough: [tutorial 3](../../tutorial/03-multi-qubit-and-labels.md)
