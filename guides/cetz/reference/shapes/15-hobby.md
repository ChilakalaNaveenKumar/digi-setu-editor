# `hobby()` — Hobby Curve

Draws a Hobby curve through the given points (the same algorithm
Metafont/MetaPost use). Smoother than Catmull-Rom for the same set of points.

## Signature

```text
hobby(
  ..pts-style: coordinate | style,
  ta:    auto | array = auto,
  tb:    auto | array = auto,
  close: bool         = false,
  name:  none | str   = none,
)
```

## Parameters

- **`..pts-style`** — positional points. Minimum two.
- **`ta`** — outgoing tension at each `pts.at(n)` (length `n - 1`).
- **`tb`** — incoming tension at each `pts.at(n+1)` (length `n - 1`).
- **`close`** — close with a smooth segment between start and end.
- **`name`** — element name.
- **`omega`** *(style)* — 2-tuple `(start, end)` of curl values. Near `0`
  approaches a straight line at the endpoints; near `1` approaches a
  circular arc.

## Styling

- **Root:** `hobby`
- Supports `mark`.

## Anchors

Path anchors plus `pt-0`, `pt-1`, … (`pt-0` ≡ `start`).

## Example

See [`examples/15-hobby/15-hobby.typ`](./examples/15-hobby/15-hobby.typ).

## Related

- [`catmull`](./14-catmull.md) — alternative smooth-fit curve
- [`hobby.hobby-to-cubic`](../internals/hobby/03-hobby-to-cubic.md) — the
  full Hobby-to-cubic-Bezier engine
- [`hobby.hobby-to-cubic-open`](../internals/hobby/01-hobby-to-cubic-open.md) /
  [`hobby.hobby-to-cubic-closed`](../internals/hobby/02-hobby-to-cubic-closed.md)
  — open / closed variants
