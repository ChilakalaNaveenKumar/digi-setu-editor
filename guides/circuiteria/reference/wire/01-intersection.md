# `wire.intersection()` — T-Junction Dot

Draws a wire intersection (a small filled dot) at the given anchor — the
standard schematic convention for "these two wires are joined here".

```text
wire.wire("w1", ((0, 0), (1, 1)), style: "zigzag")
wire.wire("w2", ((0, 0), (1, -.5)),
          style: "zigzag", zigzag-ratio: 80%)
wire.intersection("w1.zig")
```

## Signature

```text
intersection(
  pt:     point,
  radius: number = .1,
  fill:   color  = black,
) -> none
```

## Parameters

- **`pt`** — `point`. A CeTZ-compatible point or anchor (e.g.
  `"w1.zig"`, `"b1-port-out"`, or a raw `(x, y)` tuple).
- **`radius`** — `number`. The radius of the intersection dot, in
  Circuiteria units. Default `.1`.
- **`fill`** — `color`. The fill colour. Default `black`.

## Pitfalls

- The dot is drawn on top of the wires, so call `intersection(...)` *after*
  the relevant `wire(...)` calls.
- `pt` can be any CeTZ point — a wire's `<id>.zig` anchor, a port anchor,
  or a literal coordinate.

## Example

See [`examples/01-intersection/01-intersection.typ`](./examples/01-intersection/01-intersection.typ).

## Related

- [`03-wire.md`](./03-wire.md) — the `wire(...)` function whose anchors
  (`<id>.zig`, `<id>.start`, `<id>.end`) you will usually pass to
  `intersection`.
