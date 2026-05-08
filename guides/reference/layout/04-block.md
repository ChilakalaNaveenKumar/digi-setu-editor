# `block(body, ...)` — block-level container

A block-level container that can have a background, border, fixed size, or specific spacing. Blocks are also how you control whether content joins a paragraph or starts a new one (see [`par` documentation](../model/13-par.md)).

## Parameters

| Param        | Type                                | Default   | Notes                                                                  |
| ------------ | ----------------------------------- | --------- | ---------------------------------------------------------------------- |
| `width`      | `auto` / relative                    | `auto`     | `auto` = inner width                                                   |
| `height`     | `auto` / relative / fraction         | `auto`     | Fraction grows to fill remaining page height                           |
| `breakable`  | bool                                  | `true`     | Allow split across pages                                               |
| `fill`       | `none` / color / gradient / tiling   | `none`     | Background                                                             |
| `stroke`     | stroke spec                           | `(:)`      | Border (per-side dictionary supported)                                 |
| `radius`     | relative / dictionary                 | `(:)`      | Corner rounding                                                        |
| `inset`      | relative / dictionary                 | `(:)`      | Inner padding (per-side dict supported)                                 |
| `outset`     | relative / dictionary                 | `(:)`      | Expand size without affecting layout                                   |
| `spacing`    | relative / fraction                   | `1.2em`    | Shorthand for `above` + `below`                                        |
| `above`      | `auto` / relative / fraction         | `auto`     | Spacing before this block                                              |
| `below`      | `auto` / relative / fraction         | `auto`     | Spacing after this block                                               |
| `clip`       | bool                                  | `false`    | Clip overflowing content                                               |
| `sticky`     | bool                                  | `false`    | Stick to next block (no break in between). Headings are sticky by default. |
| `body`       | `none` / content                     | `none`     | Content                                                                 |

## Block vs box

| Container | Level                | Wraps with text? | Breakable across pages? |
| --------- | -------------------- | ---------------- | ----------------------- |
| `block`    | block (own line)     | No                | Yes (by default)         |
| `box`      | inline (within text) | Yes               | No                       |

## Spacing rules

`above` / `below` only kick in adjacent to other blocks. For two adjacent blocks, the **larger** of the first block's `above` and the second block's `below` wins. Block spacing **overrides** paragraph spacing.

## Common patterns

```typst
// Quote-style callout
#block(
  fill: luma(240), inset: 12pt, radius: 4pt, width: 100%,
  [Important: ...]
)

// Promote inline to block in a show rule (used for math, links, etc.)
#show math.equation: it => block(it)

// Disable heading stickiness if you want them to orphan
#show heading: set block(sticky: false)
```

## Examples (compile-verified)

- `examples/04-block/01-block.typ` — fill / inset / radius callout, promoting inline to block via show rule, `breakable: false`, sticky headings.

## Reference

https://typst.app/docs/reference/layout/block/
