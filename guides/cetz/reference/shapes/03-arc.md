# `arc()` — Circular Segment

Draws a circular segment (a piece of a circle's circumference, optionally
closed into a chord or pie slice).

## Signature

```text
arc(
  position: coordinate,
  start:  auto | angle = auto,
  stop:   auto | angle = auto,
  delta:  auto | angle = auto,
  name:   none | str   = none,
  anchor: none | str   = none,
  ..style: style,
)
```

Plus style keys:

- **`radius`** — `number | array`. Use a 2-tuple for an elliptical arc.
- **`mode`** — `"OPEN"` (default), `"CLOSE"` (chord), or `"PIE"`.
- **`update-position`** — `bool`, default `true`. When `true`, the previous
  coordinate becomes `arc-end`.

## Parameters

- **`position`** — where to place the arc.
- **`start` / `stop` / `delta`** — angles. **Exactly two of three must be
  set.** `0deg` points right, `90deg` points up.
- **`mode`** — `"OPEN"` shows just the arc; `"CLOSE"` adds a chord between
  start and end; `"PIE"` adds two lines from start/end to the origin
  (sector).

## Styling

- **Root:** `arc`
- Inherits `fill`, `stroke`, `mark`.

## Anchors

Supports border and path anchors, plus:

| Anchor | Position |
| ------ | -------- |
| `arc-start` | start of the arc curve (default) |
| `arc-end` | end of the arc curve |
| `arc-center` | midpoint of the arc curve |
| `center` | centre of the closed shape (depends on `mode`) |
| `chord-center` | midpoint of the chord between start and end |
| `origin` | centre of the underlying circle |

## Pitfalls

- Forgetting to set two of `start` / `stop` / `delta` triggers a runtime panic.
- The default `mode: "OPEN"` keeps the path open — `fill:` will still fill
  the implied chord region.

## Example

See [`examples/03-arc/03-arc.typ`](./examples/03-arc/03-arc.typ).

## Related

- [`arc-through`](./04-arc-through.md) — sibling that fits an arc to 3 points
- [`drawable.arc`](../internals/drawable/08-arc.md) — the underlying drawable
- [`util.circle-arclen`](../internals/util/07-circle-arclen.md) — arc-length math
