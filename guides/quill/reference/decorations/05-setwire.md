# `setwire()` — change wire style

Sets the current wire mode (count + stroke + bundle distance) going
forward on the current row. Resets to the circuit's default at every
`[\\ ]`.

## Signature

```typst
setwire(
  count:         int,
  stroke:        auto | none | stroke = auto,
  wire-distance: length = auto,
  x:             auto | int = auto,
  y:             auto | int = auto,
)
```

| Arg | Meaning |
| --- | ------- |
| `count` | `0` = no wire, `1` = quantum (single line), `2` = classical (two parallel), `3+` = bundle. |
| `stroke` | Stroke style; `auto` keeps the current stroke. |
| `wire-distance` | Distance between parallel lines for bundles (`count >= 2`). |
| `x` / `y` | Optional manual placement (otherwise current cursor). |

## Examples

```typst
// Switch to a classical wire mid-row.
#quantum-circuit(
  1, $H$, setwire(2), 1, gate($M$), 1
)

// "Cut" a wire then start a new one.
#quantum-circuit(
  1, $X$, setwire(0), 1, lstick($|0〉$), setwire(1), $Y$, 1
)

// Bundled wire of 3 parallel lines.
#quantum-circuit(
  setwire(3, wire-distance: 1.5pt), 1, $U$, 1
)
```

See [`examples/05-setwire/05-setwire.typ`](examples/05-setwire/05-setwire.typ).

## Pitfalls

- `setwire(0)` only affects what comes **after** — it does not erase
  drawn wire to its left.
- The wire setting **resets at every `[\\ ]`**. To keep a wire style
  on every row, repeat `setwire(...)` at the start of each row.
- `wire-distance` is only meaningful for `count >= 2`. For `count: 1`
  it is silently ignored.

## Related

- Visual bundle marker: [`nwire`](04-nwire.md)
- Tutorial: [tutorial 4](../../tutorial/04-wires.md)
