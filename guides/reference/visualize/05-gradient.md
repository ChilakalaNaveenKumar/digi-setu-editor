# `gradient` — Linear, Radial, and Conic Gradients

A `gradient` is a paint value usable anywhere a color is accepted: as
`fill`, as part of a `stroke`, or as the `fill:` of text. Three flavors:

| Constructor                | Direction model                        |
| -------------------------- | -------------------------------------- |
| `gradient.linear(..stops)` | Straight line; controlled by `angle`.  |
| `gradient.radial(..stops)` | Concentric, two-circle (focal+end).    |
| `gradient.conic(..stops)`  | Sweep around a center point.           |

## Stops

Each stop is either a bare color (Typst spaces them evenly) or a tuple of
`(color, ratio)` placing the stop at a specific position. For `gradient.conic`
the position is an angle.

> **Either every stop has an offset, or none of them does.** Mixing
> `red, (yellow, 30%), green` errors with *"either all stops must have an
> offset or none of them can"*. Spell out all four if you need any one.

```typst
#rect(width: 100%, height: 14pt,
      fill: gradient.linear((red, 0%), (yellow, 30%), (green, 100%)))
```

You can also spread a color map:

```typst
#circle(fill: gradient.linear(..color.map.viridis))
```

## Common parameters

| Parameter   | Applies to    | Default          | Notes                                      |
| ----------- | ------------- | ---------------- | ------------------------------------------ |
| `space`     | all           | `oklab`          | Interpolation color space.                 |
| `relative`  | all           | `auto`           | `"self"` (own bbox) or `"parent"` (container/page). |
| `angle`/`dir` | linear, conic | `0deg`/`ltr`   | Direction. Clockwise from "left to right". |
| `center`    | radial, conic | `(50%, 50%)`     | Anchor point.                              |
| `radius`    | radial        | `50%`            | End-circle radius.                         |
| `focal-center`/`focal-radius` | radial | `auto`/`0%` | The starting (inner) circle.        |

`relative: "parent"` is required for gradient *text* fills if you want the
gradient to span more than one glyph. Wrap glyphs in boxes (or use a show
rule) for word-by-word gradients.

## Gradient-on-text recipe

```typst
#set text(fill: gradient.linear(red, blue, relative: "parent"))
This whole paragraph is painted across one shared gradient.
```

## Methods on a gradient value

| Method                            | What it does                                           |
| --------------------------------- | ------------------------------------------------------ |
| `g.sample(t)`                     | Color at position `t` (ratio, or angle for conic).     |
| `g.samples(t1, t2, ...)`          | Array of sampled colors.                               |
| `g.sharp(steps, smoothness: 0%)`  | Discrete-step variant — great for color *lists*.       |
| `g.repeat(n, mirror: false)`      | Repeat the gradient `n` times along its direction.     |
| `g.kind()`/`g.stops()`/`g.space()`/`g.relative()`/`g.angle()`/`g.center()`/`g.radius()`/`g.focal-center()`/`g.focal-radius()` | Inspect properties (some return `none` when not applicable). |

## Tips

- For **data viz**, default to perceptually uniform maps (`viridis`, `crest`,
  `cividis`). Stay away from `rainbow`.
- For **text**, set `relative: "parent"` to share the gradient across the
  whole text instead of restarting per character.
- Need a discrete palette? `gradient.linear(..color.map.X).sharp(N)` gives
  you `N` evenly spaced colors as a sharp gradient.
- Conic gradients are sensitive to `angle`: `0deg` starts at 12 o'clock and
  proceeds clockwise.
