# `element.group()` — Bordered Group of Elements

Draws a labelled, padded border around a body of other elements. Useful
for visually clustering related blocks (a CPU stage, an FPGA region, a
sub-circuit).

```text
element.group(
  id: "g1", name: "Group 1", stroke: (dash: "dashed"),
  {
    element.block(id: "b1", w: 2, h: 2,
      x: 0, y: 1.5,
      ports: (east: ((id: "out"),)),
      fill: util.colors.green,
    )
    element.block(id: "b2", w: 2, h: 1,
      x: 0, y: 0,
      ports: (east: ((id: "out"),)),
      fill: util.colors.orange,
    )
  },
)
element.block(id: "b3", w: 2, h: 3,
  x: (rel: 1, to: "g1.east"),
  y: (from: "b1-port-out", to: "in1"),
  ports: (west: ((id: "in1"), (id: "in2"))),
  fill: util.colors.blue,
)
wire.wire("w1", ("b1-port-out", "b3-port-in1"))
wire.wire("w2", ("b2-port-out", "b3-port-in2"),
          style: "zigzag")
```

## Signature

```text
group(
  body:        elements | function,
  id:          str          = "",
  name:        str          = none,
  name-anchor: str          = "south",
  fill:        color        = none,
  stroke:      stroke       = black + 1pt,
  padding:     float | length | array | dictionary = 0.5em,
  radius:      number       = 0.5em,
) -> none
```

## Parameters

- **`body`** — `elements | function`. The elements to group. Either a
  block of `element.*` / `wire.*` / `gates.*` calls, or a function that
  produces such elements.
- **`id`** — `str`. See [`elmt()`](./01-elmt.md). Default `""`.
- **`name`** — `str`. The group's name, displayed on the outside of the
  group. Default `none`.
- **`name-anchor`** — `str`. Anchor for the name. **Note: the name is
  placed on the outside of the group.** Default `"south"`.
- **`fill`** — `color`. See [`elmt()`](./01-elmt.md). Default `none`.
- **`stroke`** — `stroke`. See [`elmt()`](./01-elmt.md). Default
  `black + 1pt`. Pass `(dash: "dashed")` for a dashed border.
- **`padding`** — `float | length | array | dictionary`. The inside
  padding:
  - **float / length** — same on all sides.
  - **array** — `(<all>,)`, `(<vertical>, <horizontal>)`, or
    `(<top>, <right>, <bottom>, <left>)`.
  - **dictionary** — valid keys: `top`, `right`, `bottom`, `left`.

  Default `0.5em`.
- **`radius`** — `number`. The corner radius. Default `0.5em`.

## Anchors

- **Compass:** `<id>.north`, `<id>.east`, `<id>.south`, `<id>.west`,
  `<id>.center` — on the *group's outer rectangle*.
- The grouped elements keep their own `id` and port anchors; the group
  does not introduce port anchors of its own.

## Pitfalls

- The group's `name-anchor` controls *where on the perimeter the label
  sits*, not where the label's own anchor is. The label is always drawn
  *outside* the border.
- The body is evaluated *before* the border is drawn, so you cannot place
  another element relative to the group's compass anchors *inside* the
  body — do that *after* the `group(...)` call (as in the example above
  with `b3`).

## Example

See [`examples/06-group/06-group.typ`](./examples/06-group/06-group.typ).

## Related

- [`03-block.md`](./03-block.md) — what you usually put inside a group.
- [`../util/04-colors.md`](../util/04-colors.md) — palette for tinting
  the inner blocks.
