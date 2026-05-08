# Export – Output Formats

Typst can export the same document to several formats. Each one is a
trade-off between fidelity, accessibility, and ecosystem fit.

| Format | Best for                                                 | Accessible? | Multi-page? |
| ------ | -------------------------------------------------------- | ----------- | ----------- |
| **PDF** (default) | Printable, archivable, structured documents.   | Yes (Tagged PDF + PDF/UA). | Yes (single file). |
| **HTML** (preview) | Web pages, semantic publishing, reflow.        | Yes (browser AT). | One file (today). |
| **PNG** | Pixel images of pages (image editing, posters, web previews). | No (raster). | Multiple PNGs. |
| **SVG** | Vector images of pages (web embedding, scalable graphics). | No (vector but not tagged). | Multiple SVGs. |

## Choosing a format

- Need a **document** people read end-to-end? → PDF (with PDF/UA-1
  if accessibility matters).
- Need to publish on the **web**, share content with web tooling, or
  produce an accessible alternative to PDF? → HTML.
- Need **bitmap images** (thumbnails, posters, slides ingested into
  another tool)? → PNG.
- Need **vector images** that scale (icons, logos, embedded diagrams,
  CSS backgrounds)? → SVG.

## Exporting from the CLI

| Format | Default if filename ends with… | Explicit flag         |
| ------ | ------------------------------- | --------------------- |
| PDF    | `.pdf` (also default)          | `--format pdf`        |
| HTML   | `.html`                         | `--format html` (requires `--features html`) |
| PNG    | `.png`                          | `--format png`        |
| SVG    | `.svg`                          | `--format svg`        |

```bash
typst compile paper.typ                # → paper.pdf
typst compile paper.typ paper.png      # → paper.png (or templated, see below)
typst compile paper.typ --format svg paper-{p}.svg
typst compile paper.typ --features html --format html paper.html
```

For multi-page documents exported to PNG or SVG, the output filename
must contain a placeholder so each page gets its own file:

| Placeholder | Replaced by                                     |
| ----------- | ----------------------------------------------- |
| `{p}`       | The page number (1, 2, 3, …)                    |
| `{0p}`      | Zero-padded page number (01, 02, 10, …)         |
| `{t}`       | Total number of pages                           |

Example: `paper-{0p}-of-{t}.png`.

## Common export options

- `--pages 2,3,7-9,11-` — comma-separated list of pages or ranges
  (half-open ranges supported).
- PDF-specific:
  - `--pdf-standard 1.7,a-2u` — pick PDF version and/or A/UA standard.
  - `--no-pdf-tags` — disable Tagged PDF (do **not** do this if you
    need accessibility).
- PNG-specific:
  - `--ppi 300` — pixels per inch (default 144).

## Exporting from the web app

Click "File → Export as → …" or use the dropdown next to the quick
download button. PDF, PNG, SVG, and (experimental) HTML are
available, with the same per-format options as on the CLI.

## Format-specific details

- [PDF →](../pdf/00-pdf-overview.md) — full PDF/A and PDF/UA
  conformance options, attachments, artifact tagging.
- [HTML →](../html/00-html-overview.md) — semantic markup, raw and
  typed element APIs, `html.frame` for inline-SVG sections.
- [PNG →](../png-svg/01-png.md) — resolution, transparent
  backgrounds.
- [SVG →](../png-svg/02-svg.md) — vector output, glyph embedding.
