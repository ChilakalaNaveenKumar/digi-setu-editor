# `wire.wire-styles` — The Three Valid Wire Styles

The `style:` argument of [`wire()`](./03-wire.md) accepts one of three
string values, exposed for introspection as `wire.wire-styles`.

```text
wire.wire-styles  // → ("direct", "zigzag", "dodge")
```

| Style | Behaviour | Extra parameters |
| ----- | --------- | ---------------- |
| `"direct"` | Straight line between the two points. | — |
| `"zigzag"` | Two-segment "stair" with a single vertical (or horizontal) corner — exposes anchor `<id>.zig`. | `zigzag-ratio` (default `50%`), `zigzag-dir` (default `"vertical"`). |
| `"dodge"` | Wire that exits the source element on `dodge-sides[0]`, runs along `y = dodge-y`, then enters the target on `dodge-sides[1]`. Useful when a straight line would cross another block. | `dodge-y` (default `0`), `dodge-sides` (default `("east", "west")`), `dodge-margins` (default `(5%, 5%)`). |

## Reproducing the manual figure

```text
for i in range(3) {
  draw.circle((i * 3, 0),     radius: .1, name: "p" + str(i * 2))
  draw.circle((i * 3 + 2, 1), radius: .1, name: "p" + str(i * 2 + 1))
  draw.content((i * 3 + 1, -1), raw(wire.wire-styles.at(i)))
}
wire.wire("w1", ("p0", "p1"), style: "direct")
wire.wire("w2", ("p2", "p3"), style: "zigzag")
wire.wire("w3", ("p4", "p5"), style: "dodge",
          dodge-y: -0.5, dodge-margins: (0.5, 0.5))
```

## Pitfalls

- `wire-styles` is a *value* — read with `wire.wire-styles`, not as a
  function call.
- Style-specific parameters are silently ignored when the style does not
  match (e.g. setting `dodge-y` on a `"direct"` wire is a no-op).

## Example

See [`examples/04-wire-styles/04-wire-styles.typ`](./examples/04-wire-styles/04-wire-styles.typ).

## Related

- [`03-wire.md`](./03-wire.md) — the function whose `style:` argument
  consumes these values.
