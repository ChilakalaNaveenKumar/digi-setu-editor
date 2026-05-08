# Accessibility Guide

Accessibility means everyone can use and understand a document —
including readers using assistive technology (AT) such as screen
readers, refreshable braille displays, screen magnifiers; readers
who reflow PDFs on a phone; readers running the document through an
LLM or repurposing it as HTML.

The principle is **Universal Access**: design from the start so the
broadest range of people and devices can read your work, instead of
retrofitting accessibility later. Most of the techniques below also
make the document better for everyone.

## What "accessible" means in practice

An accessible PDF (or HTML file) is one whose **semantic structure**
is machine-readable. AT can then announce things by role ("heading
level 2", "table with 3 columns"), navigate them, repurpose them.

Two prerequisites:

1. The format supports tagged content — both PDF and HTML do; PNG
   and SVG do not (they are pure pixel/vector raster).
2. The author used **semantic** elements (`heading`, `figure`,
   `list`, `table`, `quote`, `cite`, ...) rather than ad-hoc styling
   that only *looks* like the structure.

## Use semantic elements, always

```typst
// ❌ Don't do this
#text(size: 16pt, weight: "bold")[Heading]

// ✅ Do this
#show heading: set text(size: 16pt)
= Heading
```

Both look the same on the page; only the second is tagged as a
heading in the PDF and announced as one by AT.

Element-by-element guidance:

| Use…                    | Instead of…                                    |
| ----------------------- | ---------------------------------------------- |
| `_emph_` or `emph(...)` | `text(style: "italic", ...)` for prose stress  |
| `*strong*` or `strong(...)` | `text(weight: "bold", ...)` for prose stress |
| `list`/`enum`/`terms`   | "newline + bullet" hand-drawn lists            |
| `quote`                 | `block(...)` of quoted text                    |
| `bibliography`/`cite`   | Hand-typed reference lists                     |
| `<label>` + `@ref`      | Hand-typed "see Section 3"                     |
| `figure(caption: ...)`  | A bare image followed by hand-typed caption    |
| `table`                 | `grid` for tabular data                        |

To restyle a semantic element, use **set / show-set / show rules**.
The semantic role is preserved even with custom layout:

```typst
#show strong: set text(tracking: 0.2em, fill: blue, weight: "black")
*never forget* to secure the pegs.
```

## Reading order

PDF readers and AT consume content in **markup order**, not layout
order. For most documents this is fine. But when you use:

- [`place(...)`](../reference/layout/20-place.md)
- [`move(...)`](../reference/layout/15-move.md)
- floating figures (`figure(placement: top, ...)`)

…the visual position diverges from the markup position. Put the
function call **where you want a screen reader to announce it**,
even if that is far from where it visually appears.

## Layout containers are transparent to AT

`grid`, `stack`, `box`, `columns`, `block` carry **no semantic
meaning**. AT will read their cells linearly, in source order. This is
fine for purely decorative layout but harmful when the layout itself
*conveys meaning* (a 2×2 of options, a comparison sidebar, etc.). For
those cases, either:

- Provide an alternative textual representation in the surrounding
  prose, or
- Wrap the layout in a `figure` with a descriptive `caption` (and
  optionally an `alt:` description).

**Tabular data** belongs in `table`, not `grid`. Only `table` is
tagged as a table and navigable two-dimensionally by AT. See the
[tables guide](./03-tables.md) for accessible table construction.

`rotate`, `scale`, `skew` are also visual-only — make sure the
meaning is reachable through alt text or surrounding prose.

## Artifacts (decorative content)

Anything purely decorative (background watermarks, page-edge
ornaments, marker lines, repeated header/footer ornaments) is an
**artifact**. It must be hidden from AT.

Typst auto-tags many things as artifacts: page headers/footers,
backgrounds/foregrounds, automatic-hyphenation hyphens, repeated
table headers/footers when they re-appear. You can mark anything
else explicitly:

```typst
#pdf.artifact[#image("watermark.png")]
```

`pdf.artifact(kind: ...)` accepts `"header"`, `"footer"`, `"page"`,
or `"other"` (default). Once content is inside an artifact, you
**cannot un-mark** it for AT — split the content into semantic and
artifact parts before wrapping.

Shapes and paths (`circle`, `square`, `polygon`, `curve`, ...) are
auto-tagged as artifacts but their *content* (text, images, etc.
placed inside them) remains semantically visible. To make a *shape*
itself meaningful, wrap it in a `figure` with a descriptive `alt`.

## Color and contrast

8% of men and 0.5% of women are color-blind. Don't communicate
information **only** through color. Use:

- Patterns or icons in addition to color (chart segments, status
  indicators).
- Shape (a triangle for "warning", a circle for "info").
- Explicit text labels.

Aim for these WCAG color-contrast minimums:

| Content                                 | AA      | AAA    |
| --------------------------------------- | ------- | ------ |
| Large text (≥18 pt, or ≥14 pt bold)     | 3:1     | 4.5:1  |
| Small text                              | 4.5:1   | 7:1    |
| Non-text graphical objects              | 3:1     | 3:1    |

Use a contrast checker (e.g. [WebAIM](https://webaim.org/resources/contrastchecker/))
when in doubt. The web app's "View → Simulate color blindness" menu
helps spot color-only signaling.

## Textual representations (alt text)

Every semantic non-text element must have a textual representation,
or it is invisible to AT. The places to add it:

- **Images:** `image("...", alt: "...")`
- **Figures:** `figure(..., alt: "...")` (use this for figures that
  contain shapes, not images — when the figure contains an image,
  put the alt on the image).
- **Math:** `math.equation(alt: "...", $...$)` (required for
  PDF/UA-1 — block equations without alt text fail export).

What makes a *good* alt text:

- Brief and contextual. Match the time a sighted user would spend
  on it.
- Describe **what is visible**, not metadata or attribution.
- Don't start with "Image of…" — AT already announces the role.
- Don't repeat surrounding caption text verbatim.

```typst
// ✅ Concise, contextual, focused on the visible content.
#image("heron.jpg", alt: "Heron in flight with feet and wings spread")

// ❌ Too generic.
#image("heron.jpg", alt: "A bird")

// ❌ Includes attribution / off-image info.
#image("heron.jpg", alt: "Gray heron, photo by Makasch1966, CC-BY 4.0")
```

For **math**, describe the formula as you would read it aloud:

```typst
#math.equation(
  alt: "a squared plus b squared equals c squared",
  block: true,
  $ a^2 + b^2 = c^2 $,
)
```

For **links**, prefer descriptive link text. Avoid bare "click here"
or "more". Use the destination or topic as the link text where
possible.

## Natural language

Always set the document language so AT pronounces text correctly,
hyphenation works, and figure labels are localized. Place this
**before any content**:

```typst
#set text(lang: "de")              // German
#set text(lang: "zh", region: "HK")    // Cantonese (HK)
```

Use ISO 639 codes (prefer two-letter ISO 639-1 when available). For
mixed-language documents, scope smaller blocks:

```typst
This is #text(lang: "fr")[français].
#[
  #set text(lang: "es")
  Este es un fragmento más largo en español.
]
```

Special codes when no normal language fits: `zxx` (not natural
language), `und` (unknown), `mis` (uncoded language).

## Document title and headings

Set the title in the document metadata — it appears in the PDF
title bar, in OS file search, and contributes to PDF/UA conformance:

```typst
#set document(title: "GlorboCorp Q1 2023 Revenue Report")
```

To also display it visually, use the `title` element (with empty
parens to read the document title back):

```typst
#title()
```

**Do not** use a level-1 heading for the document title. Use `title`.
In PDF the title is tagged as the document title; level-1 headings
are tagged as section headings. In HTML export, `title` becomes
`<h1>` and a level-1 heading becomes `<h2>`.

Headings must be **sequential** — never skip levels:

```typst
// ❌
= First-level heading
=== Third-level heading       (skipped level 2)

// ✅
= First-level heading
== Second-level heading
=== Third-level heading
```

(Adobe Acrobat's accessibility checker requires outlined headings on
documents of 21+ pages.)

## Standards Typst can target

Pick the strictest one your document needs. Typst will refuse to
export when conformance rules are violated.

| Standard       | Based on PDF | Adds                                                                | When to use                                                  |
| -------------- | ------------ | ------------------------------------------------------------------- | ------------------------------------------------------------ |
| **Tagged PDF** (default) | any | Baseline structural tags                                          | Every document. Don't disable.                               |
| **PDF/UA-1**   | 1.7          | Universal Access; alt-text and title required; many auto-checks    | Documents that must be accessible. Recommended.              |
| **PDF/A-1a**   | 1.4          | Archival + accessibility; very compatible but no transparency      | Long-term archives constrained to old PDF.                   |
| **PDF/A-2a**   | 1.7          | Archival + accessibility; transparency, better reflow              | Modern archival; preferred over PDF/A-1a.                    |
| **PDF/A-3a**   | 1.7          | Like 2a, plus arbitrary file attachments                           | Archival when you need to embed source files.                |
| **PDF/A-4**    | 2.0          | Modern archival, no `a` (accessibility) level                      | Pair with PDF/UA-2 in the future.                            |

(PDF/UA-2 and Well Tagged PDF are not yet supported by Typst.)

CLI flags: `--pdf-standard ua-1`, `--pdf-standard a-2a`, etc. Cannot
mix PDF/A and PDF/UA in one export.

## Other relevant standards

- **WCAG 2.1**: web content guidelines; AA is the recommended target
  for general documents (AAA where feasible).
- **EN 301 549**: European norm; Section 10 covers non-web docs and
  cites the relevant WCAG criteria.
- **EAA (EU 2019/882)**, **ADA Title II**: legal frameworks
  requiring accessible documents in many sectors.

Targeting PDF/UA-1 covers most of the *automatable* WCAG requirements
applicable to PDF.

## Testing checklist

- [ ] `#set document(title: "...")` is set.
- [ ] `#set text(lang: "...")` is set before any content.
- [ ] No image is missing `alt: "..."`.
- [ ] No block math equation is missing `alt: "..."` (PDF/UA-1).
- [ ] Headings are sequential.
- [ ] Tabular data uses `table`, not `grid`; columns have headers.
- [ ] Color-coded info has a non-color secondary cue.
- [ ] Decorative content is wrapped in `pdf.artifact(...)`.
- [ ] Reading order matches markup order; floats / placed content are
      positioned in markup where they should be read.
- [ ] Export passes [veraPDF](https://verapdf.org/) (PDF/UA, PDF/A)
      and [PAC 2024](https://pac.pdf-accessibility.org/en) (PDF/UA, WCAG).
- [ ] Try the document with a screen reader (NVDA on Windows,
      VoiceOver on macOS).

## Limits to be aware of

- **PNG and SVG export are not accessible.** They contain no semantic
  layer. Use PDF or HTML if accessibility matters.
- **PDF in general is harder to make universally accessible than
  HTML** — PDF was conceived in 1993 for static print; tags weren't
  added until 2001. For the highest standard of access, ship an HTML
  build (currently behind `--features html`) alongside the PDF.
- **Math accessibility** in PDF requires manual `alt:` per equation
  today. Native MathML in HTML export is planned.
- **PDF images** of accessible PDF source documents are not reused —
  re-add alt text in the wrapping document.
