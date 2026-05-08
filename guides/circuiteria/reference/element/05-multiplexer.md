# `element.multiplexer()` — N-to-1 Multiplexer

Draws a multiplexer: a trapezoid with N labelled inputs on the west,
one output on the east, and a `select` port on the north or south.

```text
element.multiplexer(
  x: 0, y: 0, w: 1, h: 3,
  id: "multiplexer",
  entries: 3,
)
wire.stub("multiplexer.north", "north")
wire.stub("multiplexer-port-out", "east")

element.multiplexer(
  x: 0, y: -4, w: 1, h: 3,
  id: "multiplexer2",
  entries: ("A", "B", "C"),
)
wire.stub("multiplexer2.south", "south")
wire.stub("multiplexer2-port-out", "east")

for i in range(3) {
  wire.stub("multiplexer-port-in"  + str(i), "west")
  wire.stub("multiplexer2-port-in" + str(i), "west")
}
```

## Signature

```text
multiplexer(
  x,
  y,
  w,
  h,
  name,
  name-anchor,
  entries: int | array = 2,
  h-ratio: ratio       = 60%,
  fill,
  stroke,
  id,
  debug,
) -> none
```

For the rest of the arguments, see [`elmt()`](./01-elmt.md).

### Multiplexer-specific arguments

- **`entries`** — `int | array`. If an integer, defines the number of
  input ports (named automatically with binary indices: `00`, `01`, `10`,
  `11`, …). If an array of strings, defines the displayed name of each
  input. Default `2`.
- **`h-ratio`** — `ratio`. The height ratio of the *right* (output) side
  relative to the full height. Default `60%`.

## Built-in ports

| Anchor | Side | Notes |
| ------ | ---- | ----- |
| `<id>-port-in0`, `<id>-port-in1`, … `<id>-port-in<N-1>` | west | One per entry, top-to-bottom. |
| `<id>-port-out` | east | The selected output. |

The select line uses the bounding-box compass anchor — `<id>.north` or
`<id>.south` — rather than a port anchor.

## Pitfalls

- When `entries` is an integer, the *visible labels* are binary
  (`util.lpad(str(i, base: 2), n)`) but the *anchor names* are decimal
  (`<id>-port-in0`, `<id>-port-in1`, …). Always use the decimal name in
  wire calls.
- The select line is `<id>.north` / `<id>.south`, not `<id>-port-...`.

## Example

See [`examples/05-multiplexer/05-multiplexer.typ`](./examples/05-multiplexer/05-multiplexer.typ).

## Related

- [`04-extender.md`](./04-extender.md) — sibling trapezoidal shape.
- [`../util/01-lpad.md`](../util/01-lpad.md) — used internally for the
  binary labels.
