# `element.alu()` — Arithmetic Logic Unit

Draws an ALU with two inputs and one output. The shape is the classic
notched-on-the-west, pointed-on-the-east ALU outline.

```text
element.alu(x: 0, y: 0, w: 1, h: 2, id: "alu")
wire.stub("alu-port-in1", "west")
wire.stub("alu-port-in2", "west")
wire.stub("alu-port-out", "east")
```

## Signature

```text
alu(
  x,
  y,
  w,
  h,
  name,
  name-anchor,
  fill,
  stroke,
  id,
  debug,
) -> none
```

For a description of all arguments, see [`elmt()`](./01-elmt.md).

## Built-in ports

The `alu` shape has three fixed ports — *you do not supply a `ports:`
dictionary*:

| Anchor | Side | Notes |
| ------ | ---- | ----- |
| `<id>-port-in1` | west, upper | First input |
| `<id>-port-in2` | west, lower | Second input |
| `<id>-port-out` | east, middle | Output |

Plus the standard compass anchors `<id>.north / .east / .south / .west /
.center` on the bounding box.

## Pitfalls

- The two input port ids are literally `in1` and `in2` — *not*
  `0` / `1`.
- The shape's notch is on the *west* side; the output is on the *east*.
  Rotation is not supported by this function — for an ALU pointing the
  other way, use [`elmt`](./01-elmt.md) with a custom `draw-shape`.

## Example

See [`examples/02-alu/02-alu.typ`](./examples/02-alu/02-alu.typ).

## Related

- [`01-elmt.md`](./01-elmt.md) — base `elmt()` and the full parameter
  family.
- [`../wire/02-stub.md`](../wire/02-stub.md) — typically used to stub the
  three I/O ports.
