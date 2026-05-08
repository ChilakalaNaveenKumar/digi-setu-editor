# 03 — Sections and Subsections

> Source: <https://touying-typ.github.io/docs/tutorials/sections>

## Structure

Like Beamer, Touying maps Typst headings to *sections*, *subsections*, and
*subsubsections*. The exact mapping depends on the theme:

```typst
// dewdrop-theme: 1, 2, 3 = section, subsection, subsubsection
#show: dewdrop-theme.with(aspect-ratio: "16-9")

= Section
== Subsection
=== Title
Hello, Touying!
```

```typst
// university-theme: 1, 2 = section, slide title
#show: university-theme.with(aspect-ratio: "16-9")

= Section
== Title
Hello, Touying!
```

The control knob is `slide-level` (an int, default `2`):

```typst
// 2 = level-1 and level-2 headings both create new slides
#show: university-theme.with(config-common(slide-level: 2))

// 3 = level-1, level-2, AND level-3 headings create new slides
#show: university-theme.with(config-common(slide-level: 3))
```

## Numbering

Add numbering with Typst's built-in show rules:

```typst
#set heading(numbering: "1.1")
#show heading.where(level: 1): set heading(numbering: "1.")
```

For the much nicer "1." / "1.1" / "1.1.1" cascade, use the
[`numbly`](https://github.com/jneug/typst-numbly) helper:

```typst
#import "@preview/numbly:0.1.0": numbly
#set heading(numbering: numbly("{1}.", default: "1.1"))
```

## Table of contents

Display a TOC slide using Typst's native `outline()` wrapped in
`components.adaptive-columns` so it always fits one page:

```typst
#import "@preview/touying:0.7.3": *
#import themes.simple: *
#import "@preview/numbly:0.1.0": numbly

#set heading(numbering: numbly("{1}.", default: "1.1"))
#show: simple-theme.with(aspect-ratio: "16-9")

= Section
== Subsection

#components.adaptive-columns(outline(indent: 1em))
```

For an outline that highlights the current section, use
`components.progressive-outline()` (see
[`progress/02-sections.md`](./progress/02-sections.md)) or write your own
with `outline.entry` + `utils.section-relationship`.

## Special heading labels

Touying recognises these labels on headings:

| Label | Effect |
| ----- | ------ |
| `<touying:hidden>` | The slide is not rendered at all (content + page suppressed). |
| `<touying:no-new-section-slide>` | The heading does not create a new-section slide. |
| `<touying:unnumbered>` | The slide is not counted in the slide counter. |
| `<touying:unoutlined>` | The heading is excluded from `outline()`. |
| `<touying:no-bookmark>` | No PDF bookmark generated for this heading. |
| `<touying:handout>` | The slide is shown only in handout mode (`config-common(handout: true)`). |

Example — a hidden outline slide that does not appear in the final PDF:

```typst
== Outline <touying:hidden>
#components.adaptive-columns(outline(title: none, indent: 1em))

= First Section
== Slide One
Content.
```

## Appendix

`#show: appendix` stops the slide counter — appendix slides do not change
the total count shown in the footer:

```typst
= Main Section
== Introduction
Main content.

#show: appendix

= Appendix
== Appendix Slide
Slide number is frozen at the last main slide.
```

## Example

See [`examples/03-sections/03-sections.typ`](./examples/03-sections/03-sections.typ).

## Pitfalls

- The label syntax is case-sensitive: `<touying:hidden>`, **not**
  `<touying:Hidden>`.
- `slide-level: 2` means levels `1..=2` create slides; level-3 headings
  appear as in-slide subheadings instead.
- `set heading(numbering: ...)` should usually be set **before** the theme
  show rule, but it works either way as long as it's outside any slide block.
