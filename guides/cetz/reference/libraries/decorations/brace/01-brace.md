# `cetz.decorations.brace()` — Curly Brace Between Two Points

Draws a curly brace between `start` and `end`.

## Signature

```text
cetz.decorations.brace(
  start: coordinate,
  end:   coordinate,
  ..style: style,
  name:  string | none = none,
)
```

## Style keys

- **`amplitude`** *(number)* — height of the brace from baseline to mid spike.
- **`thickness`** *(number | ratio)* — thickness of tapered braces (relative
  to half the amplitude if a ratio).
- **`pointiness`** *(ratio)* — thickness of the mid spike.
- **`taper`** *(bool)* — when `true`, draws a tapered brace. Set
  `stroke: none` and use `fill:` for the tapered look.
- **`outer-inset`** *(number | ratio)* — inset of the outer curve points.
- **`outer-curvyness`** *(ratio)* — curvyness of the outer curves.
- **`inner-outset`** *(number | ratio)* — inset of the inner-tip curve points.
- **`inner-curvyness`** *(ratio)* — curvyness of the inner-tip curves.
- **`outer-thickness`** *(number)* — thickness of the outer tips.
- **`content-offset`** *(number)* — offset of the `content` anchor from the
  spike.
- **`flip`** *(bool)* — mirror the brace along the line between `start` and
  `end`.

## Anchors

| Anchor | Position |
| ------ | -------- |
| `start` | the `start` parameter |
| `end` | the `end` parameter |
| `spike` | tip of the spike, half-way between `start` and `end` and shifted by `amplitude` toward the brace's pointing direction |
| `content` | suggested location for label content, just past the spike |
| `center` | centre of the enclosing rectangle |

## Styling

- **Root:** `brace`

## Example

See [`examples/01-brace/01-brace.typ`](./examples/01-brace/01-brace.typ).
