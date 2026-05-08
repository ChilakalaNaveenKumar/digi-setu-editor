# `quantum-circuit()` — the circuit envelope

Top-level constructor for any Quill diagram. Children form a flat
left-to-right, wrap-on-`[\\ ]` flow, plus decorations (`slice`,
`gategroup`, `annotate`, `setwire`).

## Signature

```typst
quantum-circuit(
  wire:             stroke   = .7pt + black,
  row-spacing:      length   = 12pt,
  column-spacing:   length   = 12pt,
  min-row-height:   length   = 10pt,
  min-column-width: length   = 0pt,
  gate-padding:     length   = 0.4em,
  equal-row-heights: bool    = false,
  color:            color    = black,
  fill:             color    = white,
  font-size:        length   = 10pt,
  scale:            ratio    = 100%,
  baseline:         length | content | str = 0pt,
  circuit-padding:  length | dictionary    = 0.4em,
  wires:            auto | int | array     = auto,
  fill-wires:       bool                   = true,
  ..children: any,
)
```

## Children: what's accepted

| Child kind | Effect |
| ---------- | ------ |
| `gate(...)`, `mqgate(...)`, `meter(...)`, `ctrl(...)`, … | Gate / control symbol on the current wire. |
| `[\\ ]` (a single backslash + space content block) | New wire / row break. |
| Integer (`1`, `4`) | That many empty wire cells. |
| Length (`5pt`, `10pt`) | Horizontal gutter at this column (or vertical if right after `[\\ ]`). |
| `setwire(count, stroke, wire-distance)` | Switch wire style going forward. |
| `slice(...)`, `gategroup(...)`, `annotate(...)` | Decorations laid over the cells. |
| Plain content / strings | Centered on the wire. |
| `lstick(...)`, `midstick(...)`, `rstick(...)` | Labels at start / middle / end of the wire. |

## Layout knobs at a glance

- **Spacing** — `row-spacing`, `column-spacing`, `min-row-height`,
  `min-column-width`, `gate-padding`.
- **Theme** — `wire`, `color`, `fill`, `font-size`, `scale`.
- **Geometry** — `wires`, `fill-wires`, `equal-row-heights`,
  `circuit-padding`.
- **Inline alignment** — `baseline` (set to `"="` to align with an
  equation's `=`).

## Example

Minimal Bell-state preparation:

```typst
#quantum-circuit(
  lstick($|0〉$), $H$, ctrl(1), 1, [\ ],
  lstick($|0〉$), 1, targ(),
)
```

See [`examples/00-quantum-circuit/00-quantum-circuit.typ`](examples/00-quantum-circuit/00-quantum-circuit.typ).

## Pitfalls

- Children are **flat**. Nested arrays must be spread with `..`
  (e.g. `..tequila.build(...)` or `..range(4).map(...)`).
- A length value with no neighbouring gate has nothing to size against.
- `circuit-padding` is **outside** padding (for annotations); it is
  unrelated to `gate-padding` (inside-the-box padding).

## Related

- Per-page styling cookbook: [`reference/styling/`](../styling/00-styling-overview.md)
- Gate constructors: [`reference/gates/`](../gates/00-gates-overview.md)
- Decorations: [`reference/decorations/`](../decorations/00-decorations-overview.md)
