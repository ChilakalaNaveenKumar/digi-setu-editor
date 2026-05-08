# Wire — Overview

The wire module connects element ports together, draws unconnected stubs,
and marks T-junction intersections.

| Function | Purpose | Page |
| -------- | ------- | ---- |
| `intersection(pt, radius, fill)` | Draw a small filled dot to mark a wire intersection (T-junction). | [`01-intersection.md`](./01-intersection.md) |
| `stub(port-id, side, name, vertical, length, name-offset)` | Draw a short open-ended wire stub coming out of a port (used for unlinked I/O). | [`02-stub.md`](./02-stub.md) |
| `wire(id, pts, ...)` | Draw a wire (named, possibly bus, dashed, directed, sliced) between two CeTZ-compatible points. | [`03-wire.md`](./03-wire.md) |

Variables:

| Name | Purpose | Page |
| ---- | ------- | ---- |
| `wire-styles` | The `("direct", "zigzag", "dodge")` enum accepted by `wire(...)`. | [`04-wire-styles.md`](./04-wire-styles.md) |

## Anchor convention

Each call to `wire("w1", (a, b))` produces an element named `w1` whose
exposed anchors include:

- `w1.start` — the starting endpoint.
- `w1.end` — the ending endpoint.
- `w1.zig` — the corner of the zig-zag (only with `style: "zigzag"`).

Pass these names to subsequent `wire.intersection(...)` or other `wire(...)`
calls to chain wires.

## Pitfalls

- Wires connect *anchors*, not raw coordinates — give every block an `id`
  and reference its ports as `"<id>-port-<port-id>"`.
- The `style: "dodge"` style needs both `dodge-y:` and `dodge-margins:` to
  avoid overlapping the source / target blocks.
- `bus: true` only changes the *appearance* (a slash + bit-count label may
  be drawn) — it does not affect routing.
