# `element.block()` — Generic Block with Arbitrary Ports

Draws a rectangular block element. This is the workhorse of Circuiteria
— most diagrams are made up of `block` calls plus wires.

```text
element.block(
  x: 0, y: 0, w: 2, h: 2, id: "block",
  ports: (
    north: ((id: "clk", clock: true),),
    west:  ((id: "in1", name: "A"),
            (id: "in2", name: "B")),
    east:  ((id: "out", name: "C"),),
  ),
)
wire.stub("block-port-clk", "north")
wire.stub("block-port-in1", "west")
wire.stub("block-port-in2", "west")
wire.stub("block-port-out", "east")
```

## Signature

```text
block(
  x,
  y,
  w,
  h,
  name,
  name-anchor,
  ports,
  ports-margins,
  fill,
  stroke,
  id,
  debug,
) -> none
```

For a description of all arguments, see [`elmt()`](./01-elmt.md).

## Anchors

- **Compass:** `<id>.north`, `<id>.east`, `<id>.south`, `<id>.west`,
  `<id>.center`.
- **Ports:** `<id>-port-<port-id>` — one per port `id` declared in
  `ports`.

## `ports` dictionary cheat-sheet

```text
ports: (
  <side>: ( (id: <str>, name: <str>?, clock: <bool>?, vertical: <bool>?), ... ),
)
```

| Side | Allowed values | Direction the wire usually exits |
| ---- | -------------- | -------------------------------- |
| `north` | `("north": (...))` | up |
| `east`  | `("east":  (...))` | right |
| `south` | `("south": (...))` | down |
| `west`  | `("west":  (...))` | left |

Set `clock: true` to render a small triangle at the port (the standard
clock symbol). Set `vertical: true` to rotate the port name 90°.

## Pitfalls

- The element's *origin is its bottom-left corner*, not its centre.
- Forgetting the trailing comma on a single-element ports tuple
  (`((id: "out"),)`, not `((id: "out"))`) silently turns it into a single
  dictionary and Circuiteria will complain about port iteration.
- A clock port on a side other than `north` is rendered the same way but
  visually unusual.

## Example

See [`examples/03-block/03-block.typ`](./examples/03-block/03-block.typ).

## Related

- [`02-alu.md`](./02-alu.md) — fixed-port shorthand for the ALU shape.
- [`05-multiplexer.md`](./05-multiplexer.md) — fixed-port shorthand for
  multiplexers.
- [`../wire/03-wire.md`](../wire/03-wire.md) — connect two block ports
  with a wire.
- [`../wire/02-stub.md`](../wire/02-stub.md) — leave a port open with a
  stub.
