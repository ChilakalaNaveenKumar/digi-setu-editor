# `cetz.decorations.flat-brace()` — Flat Curly Brace

Draws a flat curly brace between two points, mimicking TikZ's
`decorations.pathreplacing` library. Uses straight line segments — better
looking than `brace` for long, low-amplitude braces.

## Signature

```text
cetz.decorations.flat-brace(
  start: coordinate,
  end:   coordinate,
  flip:  bool = false,
  debug: bool = false,
  name:  str | none = none,
  ..style: style,
)
```

## Parameters

- **`start`**, **`end`** — endpoints.
- **`flip`** — mirror the brace.
- **`debug`** — render construction geometry.
- **`name`** — element name.

## Style keys

- **`amplitude`** *(number)* — height above baseline.
- **`aspect`** *(ratio, default 50%)* — fraction of the total length where
  the spike is placed.
- **`curves`** *(number | auto | array)* — curviness factor of the brace.
  `0` = no curves.
- **`outer-curves`** *(number | auto | array)* — curviness factor of the
  outer curves only.

## Anchors

| Anchor | Position |
| ------ | -------- |
| `start` | the `start` parameter |
| `end` | the `end` parameter |
| `spike` | top of the spike |
| `content` | suggested point to place content past the spike |
| `center` | centre of the enclosing rectangle |

## Styling

- **Root:** `flat-brace`

## Example

See [`examples/02-flat-brace/02-flat-brace.typ`](./examples/02-flat-brace/02-flat-brace.typ).
