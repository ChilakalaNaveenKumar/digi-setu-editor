# Colours, dark mode (`color`, `fill`, `wire`)

Three options theme the entire circuit:

| Option | Default | Effect |
| ------ | ------- | ------ |
| `color` | `black` | Foreground for strokes, text, control dots, brackets. |
| `fill` | `white` | Default fill for gate boxes. |
| `wire` | `0.7pt + black` | Wire stroke (anything valid as a `line()` stroke). |

## Dark-mode recipe

Wrap the circuit in a black `box` and flip all three colours:

```typst
#box(fill: black, quantum-circuit(
  wire: .7pt + white,
  color: white,
  fill: black,
  1, $X$, ctrl(1), rstick([*?*]), [\ ],
  1, 1, targ(), meter(),
))
```

## Themed circuit (e.g. blue accent)

```typst
#quantum-circuit(
  color: blue.darken(20%),
  wire: .8pt + blue.darken(20%),
  fill: blue.lighten(85%),
  1, $H$, ctrl(1), 1, [\ ],
  1, 1, targ(), 1,
)
```

See [`examples/02-colors/02-colors.typ`](examples/02-colors/02-colors.typ).

## Pitfalls

- `color` controls *foreground* — wires are still styled by `wire`.
  Set both for consistency.
- A `fill: none` makes gates transparent; the wire becomes visible
  through them. For dark mode you usually want `fill: black` so the
  wire is "punched out" of gate boxes.
- Per-gate fill/stroke (`gate(body, fill: red)`) overrides the
  circuit-wide defaults.

## Related

- Per-gate options: [`gate`](../gates/01-gate.md)
- Custom rendering: [`custom-gates/`](../custom-gates/00-custom-gates-overview.md)
