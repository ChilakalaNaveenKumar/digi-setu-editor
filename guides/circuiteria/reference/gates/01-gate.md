# `gates.gate()` — Generic Logic Gate

Draws a logic gate. The shape is supplied via the `draw-shape` callback.
This function is also available as `element.gate()`.

## Signature

```text
gate(
  draw-shape:       function          = default-draw-shape,
  x:                number | dictionary,
  y:                number | dictionary,
  w:                number,
  h:                number,
  inputs:           int               = 2,
  fill:             none | color      = none,
  stroke:           stroke            = black + 1pt,
  id:               str               = "",
  inverted:         str | array       = (),
  inverted-radius:  number            = 0.1,
  debug:            dictionary        = (ports: false),
) -> none
```

## Parameters

- **`draw-shape`** — `function`. The callback used to render the gate
  outline. Default `default-draw-shape`. The shipped gate functions
  (`gate-and`, `gate-or`, …) supply specific shape callbacks.
- **`x` / `y`** — `number | dictionary`. See [`elmt()`](../element/01-elmt.md).
  Default `none` for both.
- **`w` / `h`** — `number`. Width / height. See `elmt()`. Default `none`.
- **`inputs`** — `int`. The number of inputs. Default `2`.
- **`fill`** — `none | color`. Fill colour. See `elmt()`. Default `none`.
- **`stroke`** — `stroke`. Border stroke. See `elmt()`. Default
  `black + 1pt`.
- **`id`** — `str`. The element id. See `elmt()`. Default `""`.
- **`inverted`** — `str | array`. Either the literal `"all"` (every port
  is inverted) or an array of port id strings to invert (e.g.
  `("in0", "out")`). Default `()`.
- **`inverted-radius`** — `number`. The radius of the inverted-port
  bubble. Default `0.1`.
- **`debug`** — `dictionary`. Debug options. Supported field: `ports`
  (bool, draw red dots on every port). Default `(ports: false)`.

## Built-in ports

| Anchor | Side | Notes |
| ------ | ---- | ----- |
| `<id>-port-in0`, `<id>-port-in1`, … | west | One per input. |
| `<id>-port-out` | east | The single output. |

Plus the standard compass anchors `<id>.north / .east / .south / .west /
.center`.

## Pitfalls

- The bubble drawn by `inverted:` is purely visual — port anchors stay
  in the same place whether or not the port is inverted.
- `inverted` cannot take a bare string port id — wrap single ids in an
  array: `inverted: ("in0",)`, not `inverted: "in0"`.
- The `default-draw-shape` is a plain `draw.rect` *without* `name: id`,
  so the port machinery cannot find `<id>.east` and Circuiteria panics
  with `Unknown element '<id>'`. To use bare `gate(...)` you **must
  supply a `draw-shape:` callback that calls `draw.rect(..., name: id)`**
  (or use one of the specific `gate-and` / `gate-or` / … functions).
- Reach for the specific gate functions (`gate-and`, `gate-or`, …) for
  proper logic-gate symbols.

## Example

See [`examples/01-gate/01-gate.typ`](./examples/01-gate/01-gate.typ).

## Related

- [`02-gate-and.md`](./02-gate-and.md) — the simplest specific gate.
- [`../element/01-elmt.md`](../element/01-elmt.md) — the underlying
  element machinery.
