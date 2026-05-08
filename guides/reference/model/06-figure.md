# `figure` — captioned, numbered, referenceable container

`figure(body: content, alt: none | str = none, placement: none | auto | alignment = none, scope: "column" | "parent" = "column", caption: none | content = none, kind: auto | str | function = auto, supplement: none | auto | content | function = auto, numbering: none | str | function = "1", gap: length = 0.65em, outlined: bool = true) -> content`

Wraps content with an optional caption and ties it to a counter, making it numbered and referenceable.

## Auto-detected `kind`

| Body content                | Inferred `kind` | Counter                                     |
| --------------------------- | --------------- | ------------------------------------------- |
| `image(...)`                | `image`         | `counter(figure.where(kind: image))`        |
| `table(...)`                | `table`         | `counter(figure.where(kind: table))`        |
| `raw(...)` / `` `code` ``   | `raw`           | `counter(figure.where(kind: raw))`          |
| Anything else               | `image` (default) | image counter                            |

Each kind has its own counter — table figures number `Table 1, Table 2, ...` independently of image figures.

### Custom kinds

Override `kind:` to either a string label or an element function. When using a string (or a non-table/raw/image element function), you **must** supply `supplement:` manually:

```typst
#figure(
  rect[Atom],
  caption: [A custom kind.],
  kind: "atom",
  supplement: [Atom],
)
```

## Reference syntax

A figure with a label `<key>` is referenceable via `@key` / `#ref(<key>)`. The reference picks up `kind` + `supplement` to render `Figure 1`, `Table 2`, `Atom 3`, etc.

```typst
#figure(image(...), caption: [Glacier]) <glacier>
@glacier  // -> "Figure 1"
```

## Caption customization (`figure.caption`)

The caption is a sub-element you configure independently:

| Field        | Default              | Notes                                              |
| ------------ | -------------------- | -------------------------------------------------- |
| `position`   | `bottom`             | `top` or `bottom`                                  |
| `separator`  | `auto`               | Between number and body; localized by default      |
| `body`       | (required)           | The caption text                                   |

In show rules, the caption element exposes `it.kind`, `it.supplement`, `it.counter`, `it.numbering`, `it.body`, `it.location` for full control:

```typst
#show figure.caption: it => [
  #underline(it.body) | #it.supplement
  #context it.counter.display(it.numbering)
]
```

Scope per-kind with `where`:

```typst
#show figure.where(kind: table): set figure.caption(position: top)
```

## `placement` — floating figures

| Value       | Behaviour                                                        |
| ----------- | ---------------------------------------------------------------- |
| `none`      | In-flow exactly where written (default)                          |
| `auto`      | Floats to nearest top/bottom edge                                 |
| `top`       | Floats to top of the page                                         |
| `bottom`    | Floats to bottom of the page                                      |

`scope: "parent"` makes a figure span across columns (useful in multi-column layouts).

The clearance between a floating figure and the surrounding content is set via the `place` element:

```typst
#show figure: set place(clearance: 1.5em)
```

## Page-breakable figures

Figures don't break across pages by default. To allow it (e.g. for a long table inside a figure):

```typst
#show figure: set block(breakable: true)
```

## Other knobs

| Field      | Default | Purpose                                                                 |
| ---------- | ------- | ----------------------------------------------------------------------- |
| `numbering`| `"1"`   | Pattern or function                                                       |
| `gap`      | `0.65em`| Vertical gap between body and caption                                    |
| `outlined` | `true`  | Whether `#outline(target: figure...)` includes this figure                |
| `alt`      | `none`  | Alt text for AT (PDF accessibility); avoid duplicating image's own `alt` |

## Modifying the counter

To skip / reset:

```typst
#counter(figure.where(kind: table)).update(41)
```

This resumes table numbering from 42.

## Pitfalls

- **Counter is per kind.** Mixing image and table figures in one section interleaves them visually, but they each have separate "Figure N" / "Table N" sequences.
- **Custom kinds need `supplement:` explicitly.** Otherwise `@ref` fails to localize and prints empty.
- **`placement: bottom` with too tall a body floats to the next page.** Add a paragraph or two of body text or shrink the figure.
- **`outlined: true` on custom-kind figures** still requires you to filter by that kind in `#outline(target: figure.where(kind: "atom"))` if you want them in their own list.
- **Captions on tables look better on top** for many publication styles. Set globally with the `where` show-set rule.
- **`alt:` only matters for AT.** Don't repeat what the caption already says — either give the figure a useful caption AND a useful alt, or alt-only when the body itself is non-textual (an image without a meaningful caption).

## Examples (compile-verified)

- `examples/06-figure/01-figure-with-caption.typ` — image / table / custom kind, `@ref` with localized supplements.
- `examples/06-figure/02-caption-customization.typ` — `figure.caption` set rule (separator, position-top for tables), full show-rule rendering with `it.counter.display`.
- `examples/06-figure/03-placement-and-breakable.typ` — `placement: bottom` with `set place(clearance: ...)`.

## Reference

- Official: https://typst.app/docs/reference/model/figure/
- `image`: https://typst.app/docs/reference/visualize/image/
- `table`: https://typst.app/docs/reference/model/table/
- `place` (clearance): https://typst.app/docs/reference/layout/place/
- `block` (breakable): https://typst.app/docs/reference/layout/block/
