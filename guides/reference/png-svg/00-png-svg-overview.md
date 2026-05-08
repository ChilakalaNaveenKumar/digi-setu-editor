# PNG and SVG – Image Output

PNG and SVG export turn each page of a Typst document into a
standalone image.

| Output | Bind to resolution? | Bind to a fixed font? | Multi-page?      | Accessibility? |
| ------ | ------------------- | --------------------- | ---------------- | -------------- |
| PNG    | Yes (PPI)           | No (already rasterized) | One PNG per page | None.         |
| SVG    | No (scales freely)  | Yes (text → glyph paths) | One SVG per page | None.         |

See:

- [PNG →](./01-png.md) — pixel raster output, when to choose what
  PPI, multi-page filename templates.
- [SVG →](./02-svg.md) — vector output, glyph embedding strategy,
  multi-page filename templates.
