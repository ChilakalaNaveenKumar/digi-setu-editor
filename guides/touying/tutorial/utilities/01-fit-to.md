# Utilities 01 — Fit to Height / Width

> Source: <https://touying-typ.github.io/docs/tutorials/utilities/fit-to>
>
> Thanks to [ntjess](https://github.com/ntjess) for the original code.

## `utils.fit-to-height`

Make content fill the remaining slide height:

```typst
#utils.fit-to-height(1fr)[BIG]
```

Signature:

```typst
#let fit-to-height(
  width: none,
  prescale-width: none,
  grow: true,
  shrink: true,
  height,
  body,
) = { .. }
```

Parameters:

- **`height`** *(positional, required)* — target height. Common values:
  `1fr` (fill remaining), a fixed length like `4cm`.
- **`width`** — if specified, also constrains the width *after* scaling
  (e.g. `width: 50%`).
- **`prescale-width`** — assume the content is laid out in a container of
  this width before measuring. Useful when you want a fixed reflow
  regardless of the final scale (e.g. `prescale-width: 200%` for
  twice-the-slide reflow).
- **`grow`** *(default `true`)* — allow upscaling.
- **`shrink`** *(default `true`)* — allow downscaling.
- **`body`** — the content to scale.

## `utils.fit-to-width`

Make content fill the remaining slide width — useful for titles:

```typst
#utils.fit-to-width(1fr)[#lorem(20)]
```

Signature:

```typst
#let fit-to-width(
  grow: true,
  shrink: true,
  width,
  body,
) = { .. }
```

Parameters:

- **`width`** *(positional, required)* — target width. `1fr` = full
  available width, `100%` = parent container width.
- **`grow`** / **`shrink`** — same as above.

## Practical examples

### Fitting a table to the slide

```typst
#slide[
  #utils.fit-to-height(1fr)[
    #table(
      columns: (1fr, 1fr, 1fr),
      [A], [B], [C],
      [1], [2], [3],
      [4], [5], [6],
    )
  ]
]
```

### Fitting a heading to full width

```typst
#slide[
  #utils.fit-to-width(1fr)[
    #text(weight: "bold")[A Very Long Presentation Title That Should Fill the Entire Slide Width]
  ]
]
```

## Example

See [`examples/01-fit-to/01-fit-to.typ`](./examples/01-fit-to/01-fit-to.typ).

## Pitfalls

- `fit-to-height` and `fit-to-width` measure-then-scale; very large or
  pathological content (huge tables, recursive boxes) may slow down
  compilation. Cache by hoisting the body into a `let` if you reuse it.
- `width: 50%` is *post-scale* — the body fills 50% of the parent after
  height-fitting.
- Combine with `lazy-v` only if the result would otherwise overflow;
  `fit-to-height` already changes the natural height.
