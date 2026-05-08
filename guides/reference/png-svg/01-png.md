# PNG – Pixel Raster Output

Instead of producing a PDF, Typst can render each page directly to a
**PNG** raster image. PNGs are losslessly compressed bitmaps, one
page per file. Use PNG when:

- You want to drop pages into an image editor or vector tool that
  doesn't read PDF.
- You're producing **thumbnails or previews** for the web.
- You're feeding pages into another pipeline that wants raster
  input (slide deck builder, OCR pipeline, etc.).

## Resolution

PNGs are bound to a specific resolution. You set this with
**pixels per inch (PPI)**. Typst computes the pixel dimensions of
each output PNG from each page's physical size × PPI.

Typical PPI values:

| Use case                       | PPI                  |
| ------------------------------ | -------------------- |
| Default (web preview, screen)  | **144** (Typst default) |
| Desktop printing               | 300 or 600           |
| Professional print, fine detail | 1200                 |
| Posters viewed at distance     | < 300 (e.g. 150)     |
| Modern smartphone screens      | 400 – 500            |

Below the viewing device's resolution → noticeable pixelation.
Above → big files for no visible benefit.

## Limitations

- **Not accessible.** Text in a PNG is just pixels; AT, copy/paste,
  and OCR (without external tools) cannot read it. For accessibility
  use PDF or HTML.
- **Multi-page docs produce multiple files.** Each page becomes its
  own PNG.

## Background transparency

By default, PNGs have an **opaque white** background. Make them
transparent by removing the page fill:

```typst
#set page(fill: none)
```

Useful when overlaying the PNG on another graphic or when producing
icons.

## Exporting

### CLI

```bash
typst compile slides.typ slides.png             # single-page documents only
typst compile slides.typ slides-{p}.png         # multi-page; {p} = page number
typst compile slides.typ slides-{0p}-of-{t}.png # zero-padded with total
typst compile slides.typ --ppi 300 slides-{p}.png
typst compile slides.typ --pages 2,5-7 slides-{p}.png
```

| Flag                | Effect                                                      |
| ------------------- | ----------------------------------------------------------- |
| `--format png`      | Force PNG output (or use a `.png` filename).                |
| `--ppi N`           | Pixels per inch (default 144).                              |
| `--pages <ranges>`  | Subset of pages to export.                                  |

For multi-page documents, the output filename **must** contain at
least one of:

- `{p}` — page number (1, 2, 3, ...)
- `{0p}` — zero-padded page number (01, 02, ..., 10)
- `{t}` — total page count (constant per export)

### Web app

**File → Export as → PNG**, or the dropdown next to the quick
download button. Configure PPI and page selection in the dialog.

## Common pitfalls

- **Forgetting the page placeholder.** `typst compile multi.typ
  multi.png` will fail if the document has more than one page.
  Use `multi-{p}.png` (or `--pages 1` if you really want only the
  first page).
- **Wrong PPI for the medium.** Web-only? Stay at 144. Print? Bump to
  300+. Don't routinely export at 1200 — file sizes grow ~16× from
  300 PPI.
- **Transparent background by accident.** Setting `set page(fill:
  none)` for one PDF run carries over if you also export to PNG. Be
  deliberate about transparency.
