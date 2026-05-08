# Guide for LaTeX Users

Both Typst and LaTeX are markup-based typesetting systems: you write
plain text with markup, then compile to PDF. The differences:

- Typst uses **dedicated lightweight syntax** (think Markdown) for
  common things (headings, lists, emphasis, links).
- Typst's "commands" are **uniform functions** with the same calling
  convention everywhere — no per-package conventions.
- Typst compiles in **milliseconds**, enabling real-time preview.
- Typst's standard library is **batteries-included**: most popular
  LaTeX packages have built-in equivalents.

## Installation

| Use case               | LaTeX                          | Typst                                                     |
| ---------------------- | ------------------------------ | --------------------------------------------------------- |
| Hosted, no setup       | Overleaf                       | [`typst.app`](https://typst.app/) (collaborative)         |
| Local install          | TeX Live (~3 GB)               | A single `typst` binary                                   |
| First package use      | Pre-installed                  | Downloaded on demand and cached locally                   |

## Empty document

LaTeX needs `\documentclass` + `\begin{document}` boilerplate. Typst
just needs a `.typ` file. Start typing — paragraphs separate with a
blank line.

## Markup translation table

| Element                   | LaTeX                              | Typst                                  |
| ------------------------- | ---------------------------------- | -------------------------------------- |
| Strong emphasis           | `\textbf{strong}`                  | `*strong*`                             |
| Emphasis                  | `\emph{emph}`                      | `_emph_`                               |
| Link                      | `\url{https://typst.app}`          | `https://typst.app/` (autolink)        |
| Label                     | `\label{intro}`                    | `<intro>`                              |
| Reference                 | `\ref{intro}`                      | `@intro`                               |
| Citation                  | `\cite{key}`                       | `@key`                                 |
| Inline code               | `\texttt{x}`                       | `` `x` ``                              |
| Code block                | `lstlisting` / `verbatim`          | ```` ```py ... ``` ```` or `raw(...)` |
| Bullet list               | `itemize`                          | `- item`                               |
| Numbered list             | `enumerate`                        | `+ item`                               |
| Term list                 | `description`                      | `/ Term: Description`                  |
| Figure                    | `figure` env                       | `figure(...)`                          |
| Table                     | `tabular` env                      | `table(...)`                           |
| Inline math               | `$x$`                              | `$x$`                                  |
| Display math              | `\[ x = y \]`                      | `$ x = y $` (with surrounding spaces)  |
| Heading 1/2/3             | `\section`/`\subsection`/`\subsubsection` | `= H1`, `== H2`, `=== H3`     |

Lists nest by **indentation**. A blank line between items switches a
list from "tight" to "loose" (more vertical breathing room).

## Calling functions

Typst functions are called as `name(arg1, name: value, ...)`. From
markup, prefix with `#` to drop into code mode for one expression:

```typst
First, a rectangle:
#rect()

Underline some text:
#underline([_underlined_ text])

A little maths:
#calc.max(3, 2 * 4)

Loop:
#for x in range(3) [Hi #x. ]
```

Trailing **content** arguments can move outside the parentheses:

```typst
#rect(fill: aqua)[Get started here!]   // == #rect(fill: aqua, [Get started here!])
#underline[alternative]                // empty parens omitted
```

## Argument types worth knowing

| Type     | Example                              |
| -------- | ------------------------------------ |
| content  | `[*fast* typesetting]`               |
| string   | `"Pietro S. Author"`                 |
| integer  | `23`                                 |
| float    | `1.459`                              |
| length   | `12pt`, `5in`, `0.3cm`               |
| ratio    | `65%`                                |
| color    | `red`, `rgb("#0178A4")`              |

`content` can hold markup, function calls, anything. `string` is just
a sequence of characters.

## Variables and reusable functions (`\newcommand`-style)

```typst
#let five = 5                         // simple value
#let inc(x) = x + 1                   // function definition
#let amazed(t, color: blue) = text(color)[*#t*]   // named arg + body
I have #five fingers.
If I had one more I'd have #inc(five).
```

## Affecting the rest of the document (`\bfseries`-style)

LaTeX uses *declarations* (`\bfseries text`) for "the rest of this
group is bold". Typst uses **set rules**:

```typst
I am starting out with small text.
#set text(14pt)
This is #text(18pt)[larger,] don't you think?
```

A set rule applies until the end of its containing block (or end of
file at the top level). To scope a set rule to one block, wrap it in
`#[...]`.

## "Document classes" → templates

Replace `\documentclass{article}` with an **everything-show rule**
that wraps your document in a template function:

```typst
#import "conf.typ": conf
#show: conf.with(
  title: [Towards Improved Modelling],
  authors: (
    (name: "Theresa Tungsten", affiliation: "Artos Institute",
     email: "tung@artos.edu"),
  ),
  abstract: lorem(80),
)

Let's get started!
```

Also import templates from the community registry:

```typst
#import "@preview/elsearticle:0.2.1": elsearticle
```

## Loading packages

Typst is batteries-included — most LaTeX packages map to built-ins:

| LaTeX package                  | Typst equivalent                                              |
| ------------------------------ | ------------------------------------------------------------- |
| `graphicx`, `svg`              | `image(...)`                                                  |
| `tabularx`, `tabularray`       | `table(...)`, `grid(...)`                                     |
| `fontenc`, `inputenc`, `unicode-math` | Unnecessary — just type Unicode                        |
| `babel`, `polyglossia`         | `set text(lang: "...")`                                       |
| `amsmath`                      | Built-in math mode                                            |
| `amsfonts`, `amssymb`          | `sym` module + math syntax                                    |
| `geometry`, `fancyhdr`         | `set page(...)`                                               |
| `xcolor`                       | `set text(fill: rgb("#0178A4"))`                              |
| `hyperref`                     | `link(...)`                                                   |
| `bibtex`/`biblatex`/`natbib`   | `bibliography(...)` + `cite(...)` / `@key`                    |
| `lstlisting`/`minted`          | `raw(...)` / fenced code blocks                               |
| `parskip`                      | `set par(first-line-indent: 0pt)` + `set block(spacing: ...)` |
| `csquotes`                     | `set text(lang: "...")` + `"` and `'` (auto-localized)        |
| `caption`                      | `figure(caption: ...)`                                        |
| `enumitem`                     | `set list(...)`, `set enum(...)`, `set terms(...)`            |
| `nicefrac`                     | `frac(..., style: "inline")`                                  |

For things not built-in, use the package registry:

```typst
#import "@preview/cetz:0.4.1"
```

(`@preview` is the community namespace.)

## Math

```typst
The sum from $1$ to $n$:
$ sum_(k=1)^n k = (n(n+1))/2 $
```

- Inline math: single-line `$...$`. Display math: `$ ... $` with
  spaces (or surrounding blank lines).
- In math mode, **multi-letter** identifiers are treated as
  variables (`alpha`, `beta`, `delta`, ...) — Greek/Hebrew letters
  are predefined. Single letters render verbatim.
- Use **`"..."`** for literal multi-letter text inside math:
  `$ delta "if" x <= 5 $`.
- Modifiers select alternates: `arrow.l.squiggly`. See the
  [symbols module](../reference/symbols/00-symbols-overview.md).
- Delimiters auto-scale (no `\left`/`\right`). Customize with
  [`lr(...)`](../reference/math/09-lr.md).
- A bare `/` in math becomes a fraction; redundant parens are
  elided.
- Sub/superscripts use `_`/`^`; group with parens:
  `$x_(a -> epsilon)$`.
- Drop into Typst code inside math with `#`:
  `#text(fill: maroon, 2 a b)` inside `$...$`.
- Two-dimensional argument lists use `;` for rows — that's how
  matrices work via `mat(...)`.

## "LaTeX look"

Closest Typst recipe:

```typst
#set page(margin: 1.75in)
#set par(leading: 0.55em, spacing: 0.55em,
         first-line-indent: 1.8em, justify: true)
#set text(font: "New Computer Modern")
#show raw: set text(font: "New Computer Modern Mono")
#show heading: set block(above: 1.4em, below: 1em)
```

## Bibliographies

Native support for **BibTeX `.bib`** files and Typst's own
[Hayagriva YAML](https://github.com/typst/hayagriva/blob/main/docs/file-format.md)
format. Citation styles use **CSL** (compatible with the open CSL
catalog of 80+ styles).

```typst
#bibliography("works.bib")
#cite(<key>)            // or @key

#cite(<key>, form: "prose")    // \textcite-equivalent
#cite(<key>, form: "year")     // year-only
```

## What Typst doesn't do (yet)

- **Mature plotting ecosystem** — TikZ/PGF has decades of inertia.
  The [cetz](https://typst.app/universe/package/cetz) package is the
  closest equivalent and is improving quickly.
- **Mid-page margin changes without a page break** — `set page(...)`
  starts a new page. Use [`pad(...)`](../reference/layout/19-pad.md)
  with negative padding for "stretch into the margin" effects.
