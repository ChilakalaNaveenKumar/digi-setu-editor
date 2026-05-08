# `element.extender()` — Bit-Width Extender

Draws a bit extender (the trapezoidal "sign-extend / zero-extend" symbol
with a narrow input on one side and a wide output on the other).

```text
element.extender(
  x: 0, y: 0, w: 3, h: 1,
  id: "extender",
)
wire.stub("extender-port-in", "west")
wire.stub("extender-port-out", "east")
```

## Signature

```text
extender(
  x,
  y,
  w,
  h,
  name,
  name-anchor,
  fill,
  stroke,
  id,
  h-ratio:    ratio = 75%,
  align-out:  bool  = true,
  debug,
) -> none
```

For the rest of the arguments, see [`elmt()`](./01-elmt.md).

### Extender-specific arguments

- **`h-ratio`** — `ratio`. The height ratio of the *left* (input) side
  relative to the full height. Default `75%`. Lower values make the input
  visibly narrower than the output.
- **`align-out`** — `bool`. If `true`, the output and input ports are
  vertically aligned. If `false`, the output port is centred on the right
  side. Default `true`.

## Built-in ports

| Anchor | Side | Notes |
| ------ | ---- | ----- |
| `<id>-port-in` | west | Narrow input |
| `<id>-port-out` | east | Wide output |

Plus the standard compass anchors `<id>.north / .east / .south / .west /
.center`.

## Pitfalls

- The "narrow side" is fixed to the *west*. To get a "shrinker" pointing
  the other way, use [`elmt`](./01-elmt.md) with a custom `draw-shape`.
- `h-ratio: 100%` flattens the trapezoid to a rectangle (effectively
  identical to a 1-port-each [`block`](./03-block.md)).

## Example

See [`examples/04-extender/04-extender.typ`](./examples/04-extender/04-extender.typ).

## Related

- [`03-block.md`](./03-block.md) — generic block.
- [`05-multiplexer.md`](./05-multiplexer.md) — sibling trapezoidal shape.
