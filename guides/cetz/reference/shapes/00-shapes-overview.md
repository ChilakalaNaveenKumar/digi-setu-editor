# Shapes — Overview

The drawing primitives. All accept positional `coordinate`s, named `style`
arguments, and a `name:` for later anchor lookup.

| Group | Functions |
| ----- | --------- |
| Boxed | [`circle`](./01-circle.md), [`rect`](./11-rect.md), [`grid`](./09-grid.md) |
| Free  | [`line`](./06-line.md), [`polygon`](./07-polygon.md), [`n-star`](./08-n-star.md) |
| Curves | [`bezier`](./12-bezier.md), [`bezier-through`](./13-bezier-through.md), [`catmull`](./14-catmull.md), [`hobby`](./15-hobby.md), [`arc`](./03-arc.md), [`arc-through`](./04-arc-through.md), [`circle-through`](./02-circle-through.md) |
| Composite | [`compound-path`](./16-compound-path.md), [`merge-path`](./17-merge-path.md), [`rect-around`](./18-rect-around.md), [`svg-path`](./19-svg-path.md) |
| Markers + content | [`mark`](./05-mark.md), [`content`](./10-content.md) |

## Anchors at a glance

- **Border anchors** (compass + arbitrary angles): `circle`, `rect`, `arc`,
  `ellipse`-like elements, `grid`, `group`.
- **Path anchors** (`start`, `end`, `mid`, `<n>%`): every shape that produces
  a path, i.e. all curves plus `line`, `polygon`, `n-star`, `compound-path`,
  `merge-path`, `svg-path`.
- **Custom**: `arc.arc-start/arc-end/arc-center/chord-center/origin`,
  `bezier.ctrl-n`, `catmull.pt-n`, `hobby.pt-n`, `circle-through.{a,b,c}`,
  `content.{mid,base,text,…}`, `polygon.centroid` (closed only).

## Updating the previous coordinate

Every shape updates the *previous coordinate* used by relative coordinates
(`(rel: …)`) and the empty tuple `()`. Most shapes update it to their
"natural end":

| Shape | Updates `prev` to |
| ----- | ----------------- |
| `circle`, `rect`, `polygon`, `n-star` | the centre / first positional |
| `line` | the last positional |
| `arc` | `arc-end` (override with `update-position: false`) |
| `bezier`, `bezier-through`, `catmull`, `hobby` | the curve's `end` |
| `content` | the position passed |

Override with [`move-to(pt)`](../transformation/07-move-to.md).

## Styling roots

Each shape has a single root key under `set-style(...)`:

| Shape | Root | Notable nested keys |
| ----- | ---- | ------------------- |
| `circle` / `circle-through` | `circle` | `radius`, `fill`, `stroke` |
| `rect`, `rect-around` | `rect` | `radius`, `fill`, `stroke` |
| `arc`, `arc-through` | `arc` | `radius`, `mode`, `fill`, `stroke` |
| `line`, `polygon`, `n-star` | `line` / `polygon` / `nstar` | `mark`, `fill`, `stroke` |
| `bezier*`, `catmull`, `hobby` | `bezier` / `catmull` / `hobby` | `mark`, `tension` (catmull/hobby) |
| `content` | `content` | `frame`, `padding`, `auto-scale`, `wrap` |
| `grid` | `grid` | `step`, `shift`, `help-lines`, `stroke` |
| `mark` | `mark` | `length`, `width`, `inset`, `sep`, `flip`, `reverse`, `symbol` |
| `svg-path` | `svg-path` | `fill`, `stroke` |

The full mark-style dictionary is in [`internals/mark/`](../internals/mark/).
