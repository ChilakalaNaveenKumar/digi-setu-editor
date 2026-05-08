# Advanced Styling – Building a Conference Paper

The previous two tutorials covered writing and basic formatting. This
one builds a conference-style paper from scratch by composing
**set rules**, **show-set rules**, **transformational show rules**,
and the **`context`** keyword. The result is something that meets a
strict style guide while staying easily customizable.

## The style guide we're targeting

- 11 pt serif body font
- Title: 17 pt, bold, centered
- Single-column abstract over two-column main text
- Justified body text, centered abstract
- Level-1 headings: 13 pt, centered, small caps
- Level-2 headings: italic run-ins at body size
- US Letter pages, page number centered in footer, paper title in
  the top-right of every page

## Step 1 – Page, paragraph, text setup

```typst
#set page(
  paper: "us-letter",
  header: align(right)[A Fluid Dynamic Model for Glacier Flow],
  numbering: "1",
)
#set par(justify: true)
#set text(font: "Libertinus Serif", size: 11pt)
```

Three things to notice:

- `header:` accepts arbitrary content that runs in the page's top
  margin. `align(right)` is just `align(<alignment>, <content>)`.
- `numbering: "1"` prints page numbers as Arabic numerals. Replace
  `"1"` with `"i"` for Roman, or `"(1/1)"` for "current/total".
- `set par(justify: true)` is scoped to whatever block it's in — at
  top level, that's the rest of the file.

## Step 2 – Title and authors

The `title` element is purpose-built for the **document title**
(distinct from headings, which can repeat). Don't reach for a level-1
heading here — use `title()` so screen readers and PDF metadata pick
it up correctly.

```typst
#title[A Fluid Dynamic Model for Glacier Flow]
```

Customize it with **show-set rules**. Each line targets `title` and
adjusts one independent property:

```typst
#show title: set text(size: 17pt)
#show title: set align(center)
#show title: set block(below: 1.2em)
```

Why three rules instead of one? Because each one stays *overridable
from outside* — a downstream user could keep the centering and
spacing but tweak the font size with another show-set, without
copy-pasting a transformational show rule.

Author block via `grid` (two equal columns):

```typst
#grid(
  columns: (1fr, 1fr),
  align(center)[
    Theresa Tungsten \
    Artos Institute \
    #link("mailto:tung@artos.edu")
  ],
  align(center)[
    Dr. John Doe \
    Artos Institute \
    #link("mailto:doe@artos.edu")
  ],
)
```

The trick is that `grid` takes any number of trailing content
arguments; rows are added automatically. Sizes can be `1fr`
(fraction), absolute lengths, or `auto`.

## Step 3 – Abstract

Centered, **not** justified — and the un-justify must stay scoped to
the abstract:

```typst
#align(center)[
  #set par(justify: false)
  *Abstract* \
  #lorem(80)
]
```

That `set par(justify: false)` lives only inside the surrounding
content block. The rest of the document keeps the top-level
`set par(justify: true)`.

## Step 4 – Eliminate duplication with `document` + `context`

Right now the title appears twice: once in the page header and once
in `title[...]`. Promote it to document metadata and read it back:

```typst
#set document(title: [A Fluid Dynamic Model for Glacier Flow])
#set page(
  header: align(right + horizon, context document.title),
  ...
)

#title()                  // empty parens -> use document.title
```

Notes:

- `set document(...)` records metadata used in the PDF title bar,
  PDF/UA accessibility, and OS file search.
- `title()` with empty round parens prints the registered document
  title. `title[]` would render *empty content* — round vs square
  brackets matter.
- The header uses `context document.title` because Typst can't know
  what to do with `document.title` outside a context.

## Step 5 – Two columns with a single-column "float" for the title

Wrap the body in two columns by adding `columns: 2` to the page
set rule. That would also force the title and abstract into a
column, so we hoist them out with `place(...)` using `float: true`
and `scope: "parent"`:

```typst
#set page(
  paper: "us-letter",
  header: align(right + horizon, context document.title),
  numbering: "1",
  columns: 2,
)

#place(
  top + center,
  float: true,
  scope: "parent",
  clearance: 2em,
)[
  #title()

  #grid(columns: (1fr, 1fr), ...)

  #par(justify: false)[
    *Abstract* \
    #lorem(80)
  ]
]

= Introduction
#lorem(300)

= Related Work
#lorem(200)
```

What `place` is doing:

- `top + center`: alignment for the placed content.
- `float: true`: reserve vertical space at the top of the page so
  body content doesn't overlap.
- `scope: "parent"`: use the **page** as the placement parent, not
  the current column. Without this, the title would only span one
  column.
- `clearance: 2em`: blank space between the placed block and the
  flowing content (replaces an ad-hoc `v(2em)`).

## Step 6 – Style level-1 and level-2 headings differently

Use `.where(level: ...)` to filter headings by depth. Level-1
headings get small caps, centered, 13 pt; level-2 headings become
italic run-in headers at body size.

```typst
#show heading.where(level: 1): set align(center)
#show heading.where(level: 1): set text(size: 13pt, weight: "regular")
#show heading.where(level: 1): smallcaps     // function as RHS

#show heading.where(level: 2): set text(
  size: 11pt, weight: "regular", style: "italic",
)
#show heading.where(level: 2): it => {
  it.body + [.]                              // run into the line; add a period
}
```

Two important details:

- `show heading.where(level: 1): smallcaps` uses the `smallcaps`
  function directly as the show rule's right-hand side. Equivalent
  to `it => smallcaps(it)`.
- The level-2 transformational show rule emits *just* `it.body + [.]`
  — no enclosing `block`. That's why the heading runs in with the
  body text. If you needed numbering you'd have to thread it through
  manually (`it.numbering`, `it.body`, etc.) — show rules don't
  preserve fields you don't reference.

## Putting it all together

The full document is the sum of the snippets above, in order:

1. `set document(title: [...])`
2. `set page(...)` with `paper`, `header`, `numbering`, `columns: 2`
3. `set par(justify: true)`
4. `set text(font: "Libertinus Serif", size: 11pt)`
5. Heading show-set / show rules
6. Title show-set rules
7. `place(top + center, float: true, scope: "parent")[...title +
   authors + abstract...]`
8. Body content with `= Heading` and `== Subheading`

Compile with default options and you have a paper that hits every
bullet of the style guide.

## What you learned

- How to combine `set page`, `set par`, `set text` to set the
  document baseline.
- How to use `header:` for repeated top-margin content.
- How to use `title()` and `set document(title:)` instead of a
  level-1 heading for the paper title.
- Three flavors of show rule (show-set with another `set`, a
  function as RHS like `smallcaps`, and a fully transformational
  `it => ...`) and when each is appropriate.
- `where(level: N)` selectors for targeting specific heading levels.
- `place(..., float: true, scope: "parent")` for elements that need
  to escape a multi-column layout.
- `context` for reading document metadata in a header.

Next: turn this paper into a reusable [template](./04-making-a-template.md).
