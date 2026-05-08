# `place` — overlay or float content within a container

Positions content relative to its parent container (page text area, `box`, `block`, `rect`, ...). Two modes:

- **Overlay** (`float: false`, default) — content is positioned by `alignment` and overlaid; it doesn't take normal flow space.
- **Floating** (`float: true`) — content is pushed to the top or bottom of the parent; in-flow content shifts accordingly.

## Parameters

| Param        | Type                                | Default    | Notes                                                                          |
| ------------ | ----------------------------------- | ---------- | ------------------------------------------------------------------------------ |
| `alignment`  | `auto` / alignment                   | `start`     | Anchor for placement. `auto` only with `float: true`.                          |
| `scope`      | `"column"` / `"parent"`              | `"column"`  | What container to place relative to. `"parent"` requires `float: true`.        |
| `float`      | bool                                  | `false`     | Floating layout (top/bottom of container, displacing other content).            |
| `clearance`  | length                                | `1.5em`     | Spacing between the float and surrounding flow. Only with `float: true`.        |
| `dx`         | relative                              | `0% + 0pt`  | Horizontal offset (doesn't affect layout — like `move`).                       |
| `dy`         | relative                              | `0% + 0pt`  | Vertical offset (doesn't affect layout).                                       |
| `body`       | content                               | required    | Content to place.                                                              |

## At the page top level

A top-level `place(...)` (not inside any container) positions the body **within the page's text area** (excluding margins). For positioning over the **full page** including margins, put `place(...)` inside `page.background` or `page.foreground`.

## Inline placement (in-paragraph)

`place()` inserts an invisible block-level element which can break the current paragraph. To place inside a line, wrap in a `box` of zero width and use a word joiner so spaces don't reorganize:

```typst
#let annotate(..args) = {
  box(place(..args))
  sym.wj
  h(0pt, weak: true)
}

A placed #annotate(square(), dy: 2pt) square in my text.
```

## Floating layout

```typst
#let note(where, body) = place(center + where, float: true, clearance: 6pt, rect(body))

#lorem(10)
#note(bottom)[Footnote 1]    // floats to bottom of page
#note(bottom)[Footnote 2]
#lorem(40)
```

Floats are placed in source order relative to each other and before any subsequent `place.flush()`.

## `scope: "parent"` for column spanning

In a multi-column page, `scope: "parent"` lets a float span across columns:

```typst
#set page(columns: 2)
#place(
  top + center,
  scope: "parent",
  float: true,
  text(1.4em)[Title spans both columns],
)
```

## `place.flush()`

Forces pending floats to be placed **before** continuing. Useful at section boundaries to prevent floating figures spilling into the next section.

```typst
#figure(rect(width: 100%, height: 50pt), placement: auto, caption: [...])
#place.flush()           // makes sure the figure lands BEFORE this line
This text appears after the figure.
```

## Accessibility

AT reads the placed content **at the source position** regardless of physical location. Put the markup where it makes sense for the reading order.

## Examples (compile-verified)

- `examples/20-place/01-place-overlay.typ` — overlay placement, `dx`/`dy` offsets, inline annotation pattern.
- `examples/20-place/02-place-float-and-flush.typ` — alternating top/bottom floats, `scope: "parent"` column-spanning title, `place.flush()`.

## Reference

https://typst.app/docs/reference/layout/place/
