# External — Touying Exporter

> Source: <https://touying-typ.github.io/docs/external/touying-exporter>
>
> Repo: <https://github.com/touying-typ/touying-exporter>

[touying-exporter](https://github.com/touying-typ/touying-exporter) is a
Python CLI that exports a Touying presentation (or any Typst file) to
multiple formats — HTML, PPTX, PDF, PDFPC.

## Touying Template

For online presentation hosted on GitHub Pages, use the
[touying-template](https://github.com/touying-typ/touying-template):

1. Click **Use this template** to copy the repo.
2. **Settings → Pages → Branch → None → gh-pages → Save** to enable
   GitHub Pages.
3. Visit `your-name.github.io/repo-name` to view your slides online.

> Limitation: cannot select / copy text. For text-selection support, use
> [`02-gistd.md`](./02-gistd.md) instead.

## HTML export

`touying compile <file>.typ --format html` packages the slides as SVG
images inside a single `impress.js` page. Supports GIF animations and
speaker notes.

## PPTX export

`touying compile <file>.typ --format pptx` packages PNG-rendered slides
into a `.pptx` file with speaker notes preserved.

## Install

```sh
pip install touying
```

## CLI

```text
usage: touying compile [-h] [--output OUTPUT] [--root ROOT]
                       [--font-paths [FONT_PATHS ...]]
                       [--start-page START_PAGE] [--count COUNT]
                       [--ppi PPI] [--silent SILENT]
                       [--format {html,pptx,pdf,pdfpc}]
                       [--sys-inputs SYS_INPUTS]
                       input

positional arguments:
  input                       Input file

options:
  -h, --help                  show this help message and exit
  --output OUTPUT             Output file
  --root ROOT                 Root directory for the typst file
  --font-paths [FONT_PATHS]   Paths to custom fonts
  --start-page START_PAGE     Page to start from
  --count COUNT               Number of pages to convert
  --ppi PPI                   Pixels per inch (PPTX format)
  --silent SILENT             Run silently
  --format FORMAT             html | pptx | pdf | pdfpc
  --sys-inputs SYS_INPUTS     JSON string passed to typst's sys.inputs
```

Example:

```sh
touying compile example.typ
# → example.html
```

### Passing variables to typst

```sh
touying compile example.typ --sys-inputs '{"title":"My Presentation","author":"John Doe"}'
```

In your typst file:

```typst
#let title  = sys.inputs.at("title",  default: "Default Title")
#let author = sys.inputs.at("author", default: "Default Author")

= #title
By #author
```

## Use it as a Python package

```python
import touying
touying.to_html("example.typ")
```

## Pitfalls

- HTML export wraps each slide as an SVG; very text-heavy slides may
  produce a large bundle.
- The `pdfpc` format is **JSON metadata** only — pair it with a
  `typst compile` PDF for the actual slides; see
  [`04-pdfpc.md`](./04-pdfpc.md).
- `--sys-inputs` requires valid JSON — single-quoted in shell, with
  double-quoted keys / string values.
- Custom fonts must be on the system **and** on `--font-paths` if not in
  the default Typst font search path.
