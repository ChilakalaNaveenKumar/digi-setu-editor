# `wire.stub()` — Open-Ended Wire Stub

Draws a wire stub (a short open-ended wire) coming out of a port. Useful
for unlinked I/O — for example external inputs / outputs that are not
connected to another block in the diagram.

```text
draw.circle((0, 0), radius: .1, name: "p")
wire.stub("p", "north", name: "north", length: 1)
wire.stub("p", "east",  name: "east",  vertical: true)
wire.stub("p", "south", name: "south", length: 15pt)
wire.stub("p", "west",  name: "west",  length: 3em)
```

## Signature

```text
stub(
  port-id:     str,
  side:        str,
  name:        none | str    = none,
  vertical:    bool          = false,
  length:      number        = 1em,
  name-offset: number        = 0,
) -> none
```

## Parameters

- **`port-id`** — `str`. The port anchor to stub from (e.g. `"b1-port-out"`,
  `"alu-port-in1"`, or any CeTZ-compatible anchor).
- **`side`** — `str`. The side on which the stub extends. One of
  `"north"`, `"east"`, `"south"`, `"west"`.
- **`name`** — `none | str`. Optional label drawn at the end of the stub.
  Default `none`.
- **`vertical`** — `bool`. Whether the label should be displayed vertically
  (rotated 90°). Default `false`.
- **`length`** — `number`. The length of the stub, in Circuiteria units (or
  any Typst length such as `1em`, `15pt`, `1cm`). Default `1em`.
- **`name-offset`** — `number`. The label offset, perpendicular to the
  stub. Default `0`.

## Pitfalls

- `port-id` is the *anchor name*, not the port id alone. For
  `element.block(id: "alu", ports: (east: ((id: "out"),)))` use
  `"alu-port-out"`, not `"out"`.
- `side` must agree with the side on which the port was placed; otherwise
  the stub will cross through the block.
- The `length` argument accepts either a plain number (Circuiteria units)
  or a Typst length — pick whichever scales naturally in your diagram.

## Example

See [`examples/02-stub/02-stub.typ`](./examples/02-stub/02-stub.typ).

## Related

- [`../element/03-block.md`](../element/03-block.md) — the block whose
  ports you will most often stub.
- [`../util/02-opposite-anchor.md`](../util/02-opposite-anchor.md) — useful
  when symmetrically stubbing both sides of an element.
