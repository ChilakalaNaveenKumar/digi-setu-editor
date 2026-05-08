# `outline` — table of contents (or list of any element)

`outline(title: none | auto | content = auto, target: label | selector | location | function = heading, depth: none | int = none, indent: auto | relative | function = auto) -> content`

Generates a list of every occurrence of a given element kind, with their numbering and page numbers.

```typst
#set heading(numbering: "1.")
#outline()
= Introduction
= Methods
== Setup
```

## Parameters

| Field    | Default   | What it does                                                                  |
| -------- | --------- | ----------------------------------------------------------------------------- |
| `title`  | `auto`    | `auto` = localized "Contents". `none` = no title. Or pass content.            |
| `target` | `heading` | What to list. Element function or selector. See `where(...)` examples below.   |
| `depth`  | `none`    | Max nesting level. `none` = unlimited                                          |
| `indent` | `auto`    | `auto` = align prefix with parent's body. Or fixed length, or function `(level) -> length` |

## Listing things other than headings

`target:` accepts any element function or selector:

| `target:` value                              | Listing                            |
| -------------------------------------------- | ---------------------------------- |
| `heading` (default)                          | Table of contents                  |
| `figure`                                     | All figures                        |
| `figure.where(kind: image)`                  | Image figures only                 |
| `figure.where(kind: table)`                  | Table figures only                 |
| `math.equation.where(numbering: "(1)")`      | Numbered equations                  |

```typst
#outline(title: [List of Figures], target: figure.where(kind: image))
```

## Numbering the outline heading

Outlines (and bibliographies) don't get heading numbering by default. Force it:

```typst
#show outline: set heading(numbering: "1.")
```

## Styling outlines

`outline.entry` is one entry. The default show rule is:

```typst
#show outline.entry: it => link(
  it.element.location(),
  it.indented(it.prefix(), it.inner()),
)
```

Helpers on the entry value:

| Helper            | Returns                                                  |
| ----------------- | -------------------------------------------------------- |
| `it.indented(p, i)` | Indented layout combining a prefix and inner content    |
| `it.prefix()`     | Number + supplement (e.g. `1.1` for headings, `Figure 1`) |
| `it.inner()`      | Body + fill leader + page number                          |
| `it.body()`       | Just the title text                                       |
| `it.page()`       | Just the page number                                      |
| `it.fill`         | Fill content (defaults to dotted repeat)                  |

### Common customizations

```typst
// Bold + spaced top-level entries
#show outline.entry.where(level: 1): it => {
  v(0.4em, weak: true)
  strong(it)
}

// Solid line instead of dotted leader
#set outline.entry(fill: box(width: 1fr)[#line(length: 100%, stroke: 0.4pt)])

// Drop fill + page numbers entirely
#show outline.entry: it => link(
  it.element.location(),
  it.indented(it.prefix(), it.body()),
)
#set outline.entry(fill: none)
```

The `fill` field is placed inside a fractional box `1fr` between body and page number. When wrapping it in a custom show rule, also wrap any custom fill in `box(width: 1fr, ...)` to keep the spacing right.

## Pitfalls

- **Outlines see only `outlined: true` elements.** A heading with `outlined: false` is hidden from the outline (and from PDF bookmarks unless `bookmarked: true`).
- **`target: heading` is the default**, so `#outline()` is a TOC. `#outline(target: figure)` lists every figure of any kind — usually you want the `where(kind: ...)` filtered version.
- **`depth` only affects the outline display**, not which elements are outlined. To skip elements entirely from EVERY outline, use `outlined: false` on those elements.
- **Customizing the entry layout is finicky.** The default `it.indented(...)` is doing a lot — replicate it (or call it) before swapping pieces. Use the helpers (`prefix`, `inner`, `body`, `page`) rather than reconstructing strings yourself.
- **Equation outlines have no body**, so the default rule still works but doesn't run through `indented()` for them.
- **Multiple `#outline()` calls** are supported (e.g. one TOC + one List of Figures + one List of Tables).

## Examples (compile-verified)

- `examples/12-outline/01-toc-and-targets.typ` — TOC with `depth: 2`, separate List of Figures and List of Tables via `figure.where(kind: ...)`.
- `examples/12-outline/02-styling-entries.typ` — bold + extra space on level-1 entries, solid-line fill, second outline that drops page numbers entirely.

## Reference

- Official: https://typst.app/docs/reference/model/outline/
- `heading.outlined` / `heading.bookmarked`: https://typst.app/docs/reference/model/heading/
- `figure.outlined`: https://typst.app/docs/reference/model/figure/
- `repeat` (used by default fill): https://typst.app/docs/reference/layout/repeat/
