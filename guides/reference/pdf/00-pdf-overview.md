# PDF – Overview, Standards, and the `pdf` Module

PDF is Typst's **default** export format. PDFs render the same on
every device, support text extraction and accessibility tags, and
are the natural output for printed and archival documents. Unlike
PNGs, PDFs are not bound to a specific resolution.

## Exporting

### CLI

```bash
typst compile paper.typ                      # → paper.pdf
typst compile paper.typ --pages 1-3,7
typst compile paper.typ --pdf-standard ua-1
typst compile paper.typ --pdf-standard a-2u,1.7
typst compile paper.typ --no-pdf-tags        # NOT recommended
```

| Flag                 | Effect                                                                  |
| -------------------- | ----------------------------------------------------------------------- |
| `--pdf-standard <s>` | Comma-separated PDF version(s) and conformance levels.                  |
| `--pages <ranges>`   | Subset of pages to export.                                              |
| `--no-pdf-tags`      | Disable Tagged PDF (breaks accessibility and PDF/A-a / PDF/UA).         |

Valid `--pdf-standard` values: `1.4`, `1.5`, `1.6`, `1.7` (default),
`2.0`, `a-1b`, `a-1a`, `a-2b`, `a-2u`, `a-2a`, `a-3b`, `a-3u`,
`a-3a`, `a-4`, `a-4f`, `a-4e`, `ua-1`.

### Web App

Quick download → PDF (default settings) or **File → Export as →
PDF** for full options. Same configuration as the CLI.

## PDF versions

Typst writes PDF 1.7 by default. You can also target 1.4, 1.5, 1.6,
or 2.0. Each newer version improves something:

| Version      | Improves over 1.4                                                  |
| ------------ | ------------------------------------------------------------------ |
| **1.5** (2003) | Color management, text extraction, table accessibility, reflow, emoji fonts. |
| **1.6** (2004) | More flexible links.                                             |
| **1.7** (2006) | File [attachments](./02-attach.md), better reflow.               |
| **2.0** (2017) | Improved metadata + tag semantics for accessibility.             |

When embedding PDFs as [images](../visualize/06-image.md), the
exported PDF version must be **≥** the embedded files'.

For general distribution, leave the default 1.7 (or pick 2.0 if you
need its features).

## Accessibility standards

Typst can enforce conformance with PDF/A and PDF/UA standards. You
can target **one PDF/A part and conformance level** at a time. PDF/A
and PDF/UA cannot be combined in a single export today.

### PDF/UA-1 (recommended for accessible documents)

PDF/UA describes how to write a PDF for **Universal Access**. PDF/UA-1
is based on PDF 1.7. Selecting it:

- Forces Tagged PDF.
- Enforces alt text on images.
- Enforces alt text on math equations (`math.equation(alt: ...)`).
- Requires a document title (`#set document(title: ...)`).
- Runs other auto-checks (heading sequence, etc.).

What PDF/UA can't auto-check (but you must do):

- Set the language: `#set text(lang: "..")` before any content.
- Use semantic elements (headings, figures, lists) instead of
  hand-styled lookalikes — see the
  [accessibility guide](../../guides/04-accessibility.md).
- Don't communicate solely with color, format, or layout.
- Wrap decorative content in [`pdf.artifact(...)`](./01-artifact.md).
- Don't use images of text.

### PDF/A (archival)

Multiple parts and conformance levels:

| Profile     | Based on PDF | Notes                                                       |
| ----------- | ------------ | ----------------------------------------------------------- |
| **A-1b**    | 1.4          | Basic archival; no transparency.                            |
| **A-1a**    | 1.4          | Adds Tagged PDF + accessibility (text must map to Unicode). |
| **A-2b**    | 1.7          | Basic archival on PDF 1.7.                                  |
| **A-2u**    | 1.7          | A-2b + Unicode-mappable text. **Prefer over A-2b.**         |
| **A-2a**    | 1.7          | A-2u + Tagged PDF + no Private Use Area chars.              |
| **A-3b/u/a**| 1.7          | A-2 + arbitrary file [attachments](./02-attach.md).         |
| **A-4**     | 2.0          | Modern archival; no `a` accessibility level — pair with PDF/UA-2 (future). |
| **A-4f**    | 2.0          | A-4 + attachments.                                          |
| **A-4e**    | 2.0          | A-4f + 3D content (Typst doesn't emit 3D).                  |

### Choosing a PDF/A profile (decision tree)

1. Does pre-2006 software / equipment need to read it?
   → **A-1** (most compatible; PDF 1.4).
2. Otherwise, do you need attachments?
   → **A-3** (or **A-4f** for PDF 2.0).
3. Otherwise, do you need PDF 2.0 features?
   → **A-4** (no attachments) or **A-4f** (with).
4. Otherwise, choose **A-2** (modern, broad compat).

Then pick a conformance level:

- **`a`** for accessibility (preferred).
- **`u`** if your file is inherently inaccessible (e.g. an artist's
  portfolio) but text is Unicode-mappable.
- **`b`** as a last resort if `u` produces compiler errors (rare,
  e.g. you intentionally use Private Use Area characters).

For PDF/A-4, just choose A-4 unless you need attachments.

## The `pdf` module

PDF-specific functions live in the global `pdf` module. They tag
content with PDF-specific accessibility metadata.

| Definition                                  | Purpose                                              |
| ------------------------------------------- | ---------------------------------------------------- |
| [`pdf.artifact`](./01-artifact.md)          | Mark content as decorative (hidden from AT).         |
| [`pdf.attach`](./02-attach.md)              | Attach an external file to the output PDF.           |
| [`pdf.data-cell`](./03-data-cell.md)        | Mark a cell inside `table.header` as a *data* cell.  |
| [`pdf.header-cell`](./04-header-cell.md)    | Mark a cell as a *header* cell with a chosen scope.  |
| [`pdf.table-summary`](./05-table-summary.md) | Attach an AT-only summary to a complex table.       |

### `a11y-extras` feature flag

`pdf.data-cell`, `pdf.header-cell`, and `pdf.table-summary` are
**experimental**. To use them today, enable the `a11y-extras`
feature:

```bash
typst compile paper.typ --features a11y-extras
# or
TYPST_FEATURES=a11y-extras typst compile paper.typ
```

These functions may move out of the `pdf` module (to make their
information available to HTML export too) or change shape in a future
release. Watch the release notes.
