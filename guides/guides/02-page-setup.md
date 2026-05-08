# Page Setup Guide

Margins, columns, headers, footers, page numbers — all driven by a
single set rule on `page`. Specifying it at the top of the document
(or in a template) ensures all pages are consistent. A page set rule
mid-document **forces a new page** with the new layout, so pin it at
the start.

## Page size

```typst
#set page("us-letter")        // by ISO/standard name
#set page(width: 12cm, height: 12cm)   // custom
```

Common keywords: `"a3"`–`"a6"`, full ISO 216 (`"iso-c2"` etc.),
`"us-letter"`, `"us-legal"`, `"presentation-16-9"`, plus many regional
sizes — see the `paper` parameter on
[`page`](../reference/layout/18-page.md).

## Margins

```typst
#set page(margin: 2cm)                                // all four sides
#set page(margin: (top: 3cm, bottom: 2cm, x: 1.5cm))  // by side
```

Margin dictionary keys:

- `top`, `bottom`, `left`, `right` — individual sides.
- `x` — both `left` and `right`.
- `y` — both `top` and `bottom`.
- `inside` / `outside` — relative to the binding (see below).
- `rest` — fill in the unset sides (handy default).

Example: `(left: 1.5in, rest: 1in)` sets the left margin to 1.5″ and
the other three sides to 1″.

## Alternating margins for bookbinding

`inside` always points toward the spine, `outside` toward the page
edge. Typst infers binding side from text language (`set text(lang:
...)`) but you can override:

```typst
#set page(margin: (inside: 2.5cm, outside: 2cm, y: 1.75cm))
#set page(binding: right)        // override (e.g. English-text manga)
```

If `binding: left` (default for LTR scripts), `inside` is on the
**left** for odd pages and on the **right** for even ones, and vice
versa for `binding: right`.

## Headers and footers

```typst
#set page(header: [
  _Lisa Strassner's Thesis_  #h(1fr)  National Academy of Sciences
])
```

Headers are **bottom-aligned** by default (so they don't crash into
the page edge). Wrap in `align(top, ...)` (or `top + center`, etc.)
if you need a different vertical position.

`h(1fr)` is the workhorse for "spread to the available width": the
fractional spacer expands to fill the line.

### Conditional headers (skip the title page)

Use `context` + the page counter:

```typst
#set page(header: context {
  if counter(page).get().first() > 1 [
    _Lisa Strassner's Thesis_  #h(1fr)  National Academy of Sciences
  ]
})
```

The page counter is single-level, so `.first()` extracts the integer
page number. `> 1` skips page 1; replace with `else` to render an
alternative on the title page.

### Adapt to specific elements (omit header on big-table pages)

Combine `context`, `query`, and labels:

```typst
#set page(header: context {
  let matches = query(<big-table>)
  let here = counter(page).get()
  let on-this-page = matches.any(m =>
    counter(page).at(m.location()) == here)
  if not on-this-page [_Lisa Strassner's Thesis_  #h(1fr)  Academy]
})

... #table(...) <big-table>
```

## Page numbers

Quickest path:

```typst
#set page(numbering: "1")          // 1, 2, 3, ...
#set page(numbering: "i")          // i, ii, iii, ...
#set page(numbering: "— 1 —")      // dashes around the number
#set page(numbering: "1 of 1")     // "1 of 12", "2 of 12", ...
```

Position with `number-align: center | left | right` (default
`center`).

### Custom footer with the page number

When the **`footer`** argument is given, `numbering` is ignored;
build the page number into the footer yourself:

```typst
#set page(footer: context [
  *American Society of Proceedings*
  #h(1fr)
  #counter(page).display("1/1", both: true)
])
```

`counter(page).display(pattern, both: true)` substitutes the current
page number for the first digit position and the **total** page count
for any second digit position.

### Reset / skip page numbers

```typst
#counter(page).update(1)             // restart at 1 (forces a page)
#counter(page).update(n => n + 5)    // skip ahead by 5
```

`counter` returns the formatted *display* counter — distinct from
the actual page index. For the actual page index, read
`here().page()` inside a context block.

## Columns

For a multi-column body, set the count on the page:

```typst
#set page(columns: 2)
#set columns(gutter: 12pt)
```

For a **single-column title with a two-column body**, place the
title with `float: true` and `scope: "parent"`:

```typst
#set page(columns: 2)
#place(top + center, float: true, scope: "parent",
       text(1.4em, weight: "bold")[Impacts of Odobenidae])
== About seals
#lorem(80)
```

For columns inside a nested container (a rectangle, a sidebar, ...)
use the `columns(...)` function directly:

```typst
#rect(width: 6cm, height: 3.5cm,
      columns(2, gutter: 12pt)[ ... ])
```

(But at the page level, the `set page(columns: ...)` form is
preferred — it integrates with floats, footnotes, and line numbers.)

### Balanced columns

Typst doesn't auto-balance the last page. Insert
[`#colbreak()`](../reference/layout/06-colbreak.md) where you want the
break to fall manually.

## One-off page overrides (landscape, custom margin, ...)

Call `page(...)` as a function with the override and the content:

```typst
#page(flipped: true)[
  = Multiplication table

  #table(
    columns: 5 * (1fr,),
    ..for x in range(1, 10) {
      for y in range(1, 6) { (str(x*y),) }
    }
  )
]
```

Typst inserts as many pages with the overrides as the content needs,
then reverts to the surrounding `set page(...)`.

## Advanced layout knobs

| Knob                              | Use                                                  |
| --------------------------------- | ---------------------------------------------------- |
| `header-ascent` / `footer-descent` | Distance from the header/footer to the body box.   |
| `fill: none`                       | Transparent background (for PNG/SVG output).        |
| `flipped: true`                    | Landscape orientation.                              |
| `background:` / `foreground:`      | Watermark or overlay content on every page.         |
| `page-numbering` (via `set document(...)`) | Override the document-wide numbering pattern. |

## Recipe: typical academic paper

```typst
#set page(
  paper: "us-letter",
  margin: (top: 2.5cm, bottom: 2.5cm, x: 2cm),
  numbering: "1",
  header: align(right, smallcaps[paper short title]),
)
#set par(justify: true, leading: 0.7em)
#set text(font: "Libertinus Serif", size: 11pt)
#show heading.where(level: 1): set block(above: 1.4em, below: 0.8em)
```

That's the baseline most templates start from. Layer columns,
floats, conditional headers as needed.
