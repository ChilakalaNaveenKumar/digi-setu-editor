# SVG – Scalable Vector Output

Instead of producing a PDF, Typst can render each page directly to a
**scalable vector graphic (SVG)**. SVGs preserve the page's vector
data, so you can scale them to any size without quality loss — the
preferred format for embedding Typst output in web pages or other
SVG-aware tools.

## How text is embedded

SVGs can carry text in two ways:

- As **text elements** rendered with the viewer's local fonts, or
- As **glyph paths** (vector shapes for each character).

Typst chooses **glyph paths**. This guarantees the SVG renders
identically across devices regardless of which fonts the viewer has
installed. The trade-off: text in the SVG is **not extractable**
(no copy/paste, no screen-reader access). For accessible output use
PDF or HTML.

## When to use SVG

- Embedding rendered Typst output in a **web page** as a vector image.
- Producing **scalable icons / diagrams** for use in other tools
  (Sketch, Figma, Inkscape, Adobe Illustrator).
- Pipelines that prefer vector input (PDF→print workflows that want
  SVG intermediates).
- When you need **infinitely scalable** rendering without raster
  artifacts (PDF works too, but SVG is more web-native).

## When NOT to use SVG

- **Anything text-extraction-sensitive** (search, accessibility,
  copy-paste). Use PDF or HTML.
- Multi-page documents you want as a *single file*. SVG is
  one-per-page; PDF is one file for everything.
- Documents with a lot of text that would benefit from native font
  rendering (better legibility on phones, accessibility) — favour PDF.

## Background transparency

Default: opaque white. To remove the background:

```typst
#set page(fill: none)
```

Useful for icons or for overlaying SVGs on other content in
the consuming app.

## Exporting

### CLI

```bash
typst compile slides.typ slides.svg             # single-page documents only
typst compile slides.typ slides-{p}.svg         # multi-page (one per page)
typst compile slides.typ slides-{0p}-of-{t}.svg # zero-padded + total
typst compile slides.typ --pages 2,5-7 slides-{p}.svg
```

| Flag                | Effect                                                      |
| ------------------- | ----------------------------------------------------------- |
| `--format svg`      | Force SVG output (or use a `.svg` filename).                |
| `--pages <ranges>`  | Subset of pages to export.                                  |

For multi-page documents, the output filename **must** contain at
least one of:

- `{p}` — page number (1, 2, 3, ...)
- `{0p}` — zero-padded page number (01, 02, ..., 10)
- `{t}` — total page count

### Web app

**File → Export as → SVG**, or the dropdown next to the quick
download button. Configure page selection in the dialog.

## Tips

- **For inline embedding in HTML pages**, prefer
  [`html.frame(...)`](../html/02-frame.md) inside an HTML build
  rather than exporting separately and `<img src="..">`-ing the
  result. The frame approach lets the surrounding HTML stay
  semantic.
- **For shipping diagrams to designers**, SVG is the lingua franca —
  but remember that text is glyph paths. If a designer wants to edit
  text labels, render those labels as separate text elements in the
  destination tool instead of relying on the SVG glyphs.
- **For very large documents**, SVG file size grows with content
  complexity (every shape, every glyph path). PDF compresses better
  for text-heavy multi-page output.
