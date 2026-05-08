# `ellipse()` — Drawing Ellipses

`ellipse` is `circle`'s rectangular cousin: same parameters, but `width`
and `height` may differ. With no body it defaults to a `45pt × 30pt` box.

## Signature

```text
ellipse(
  width:  auto | relative = auto,
  height: auto | relative | fraction = auto,
  fill:   none | color | gradient | tiling = none,
  stroke: none | auto | length | color | gradient | stroke | tiling | dictionary = auto,
  inset:  relative | dictionary = 0% + 5pt,
  outset: relative | dictionary = (:),
  body:   none | content = none,
) -> content
```

`width`/`height` accept ratios (`width: 50%`) so the ellipse stretches with
its container. There is no `radius` shortcut — for a circle, use
[`circle`](./01-circle.md) instead.

## Same defaults as the other shapes

- Setting `fill` removes the default 1pt stroke.
- `inset` adds invisible padding inside the ellipse (default `0% + 5pt`).
- `outset` enlarges the ellipse without affecting layout.

## Useful for

- Speech bubbles and callouts (text inside an ellipse with `inset`).
- Decorative bullets that aren't perfectly round.
- Highlight blobs around words or short phrases.
