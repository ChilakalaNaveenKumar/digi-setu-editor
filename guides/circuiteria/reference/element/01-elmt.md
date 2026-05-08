# `element.elmt()` — The Base Element

Draws a generic element. All other element functions (`block`, `alu`,
`extender`, `multiplexer`, the gate family) are thin wrappers around this
that supply a specific `draw-shape` callback.

## Signature

```text
elmt(
  draw-shape:    function     = default-draw-shape,
  x:             number | dictionary,
  y:             number | dictionary,
  w:             number,
  h:             number,
  name:          none | str   = none,
  name-anchor:   str          = "center",
  ports:         dictionary   = (:),
  ports-margins: dictionary   = (:),
  fill:          none | color = none,
  stroke:        stroke       = black + 1pt,
  id:            str          = "",
  auto-ports:    bool         = true,
  ports-y:       dictionary   = (:),
  debug:         dictionary   = (ports: false),
) -> none
```

## Parameters

- **`draw-shape`** — `function`. The callback used to draw the element's
  outline. Default is `default-draw-shape`, which draws a plain rectangle.
- **`x`** — `number | dictionary`. The x position of the bottom-left
  corner. If a dictionary, use `(rel: number, to: str)` where `rel` is the
  offset and `to` the base anchor. Default `none`.
- **`y`** — `number | dictionary`. The y position of the bottom-left
  corner. If a dictionary, use `(from: str, to: str)` where `from` is the
  base anchor and `to` is the id of the port to align with the anchor.
  Default `none`.
- **`w`** — `number`. The element's width, in Circuiteria units. Default
  `none`.
- **`h`** — `number`. The element's height, in Circuiteria units. Default
  `none`.
- **`name`** — `none | str`. Optional name displayed inside the element.
  Default `none`.
- **`name-anchor`** — `str`. Anchor for the optional name. Default
  `"center"`.
- **`ports`** — `dictionary`. Dictionary of ports keyed by cardinal
  direction (`"north"`, `"east"`, `"south"`, `"west"`); each value is an
  array of port dictionaries with the following fields:

  | Field | Type | Notes |
  | ----- | ---- | ----- |
  | `id` | `str` | **(required)** — port id (becomes part of the anchor `"<element-id>-port-<id>"`). |
  | `name` | `str` | optional name displayed inside the block, beside the port. |
  | `clock` | `bool` | whether it is a clock port (drawn with the small triangle symbol). |
  | `vertical` | `bool` | whether the port name should be drawn vertically. |

  Default `(:)`.
- **`ports-margins`** — `dictionary`. Dictionary of port margins (used
  with automatic port placement). Keys are cardinal directions; values are
  tuples `(<start>, <end>)` of margins (numbers). Default `(:)`.
- **`fill`** — `none | color`. Fill colour. Default `none`.
- **`stroke`** — `stroke`. Border stroke. Default `black + 1pt`.
- **`id`** — `str`. The element's id, for future anchor references.
  Default `""`.
- **`auto-ports`** — `bool`. Whether to use automatic port placement. If
  `false`, the `draw-shape` callback is responsible for adding the
  appropriate ports. Default `true`.
- **`ports-y`** — `dictionary`. Dictionary of explicit port y offsets
  (only used when `auto-ports: false`). Default `(:)`.
- **`debug`** — `dictionary`. Dictionary of debug options. Supported
  fields:
  - **`ports`** — `bool`. If `true`, shows dots on all ports of the
    element. Default `false`.

  Default `(ports: false)`.

## Anchors

- **Compass:** `<id>.north`, `<id>.east`, `<id>.south`, `<id>.west`,
  `<id>.center` — provided automatically by the underlying CeTZ rect.
- **Ports:** `<id>-port-<port-id>` — one per `id` declared in `ports`.

## Pitfalls

- Most diagrams reach for [`block`](./03-block.md) instead — `elmt` is
  there if you need to plug in a custom `draw-shape`.
- The default `draw-shape` is a no-op (`(f, tl, tr, br, bl)` with `f =
  {}`). Calling `elmt(...)` without supplying your own `draw-shape:`
  draws nothing *and* registers no CeTZ element — any subsequent
  `wire.stub("<id>-port-...", ...)` then panics with `Unknown element
  '<id>'`. Either supply a `draw-shape:` callback that invokes
  `draw.rect(..., name: id)` (see [`examples/01-elmt/01-elmt.typ`](./examples/01-elmt/01-elmt.typ))
  or use one of the prebuilt elements (`block`, `alu`, `multiplexer`, …).
- `x` / `y` accept either a literal number *or* a relative-placement
  dictionary; mixing the two on a single element is allowed.
- Setting `id: ""` (the default) means port anchors collapse to
  `"-port-<port-id>"` and may collide with other unnamed elements. Always
  set `id:`.

## Example

See [`examples/01-elmt/01-elmt.typ`](./examples/01-elmt/01-elmt.typ).

## Related

- All other element functions (`block`, `alu`, `extender`, `multiplexer`,
  the gate family) inherit this parameter family.
