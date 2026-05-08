# External Tools — Overview

> Source: <https://touying-typ.github.io/docs/category/external-tools>

These are external tools / services that work *with* Touying — they are
not Typst packages but rather command-line tools, browser viewers, or
LSP integrations.

| File | Tool | Use |
| ---- | ---- | --- |
| [`01-touying-exporter.md`](./01-touying-exporter.md) | [`touying-exporter`](https://github.com/touying-typ/touying-exporter) | Python CLI that exports a Touying `.typ` to HTML, PPTX, PDF, or PDFPC. |
| [`02-gistd.md`](./02-gistd.md) | [`gistd`](https://github.com/Myriad-Dreamin/gistd) | Browser-based viewer that renders any GitHub Typst file as live slides (with text-selection support). |
| [`03-pympress.md`](./03-pympress.md) | [`pympress`](https://github.com/Cimbali/pympress) | Dual-screen PDF presenter for talks, with speaker notes. |
| [`04-pdfpc.md`](./04-pdfpc.md) | [`pdfpc`](https://pdfpc.github.io/) | Multi-monitor PDF presenter console. Touying writes the JSON metadata file. |
| [`05-typst-preview.md`](./05-typst-preview.md) | Tinymist's *Typst Preview* | VS Code panel + browser slide-mode for live preview while editing. |

## Quick reference

| Need | Tool |
| ---- | ---- |
| Export PDF for distribution | `typst compile` (built-in) or `touying-exporter` |
| Export to PowerPoint (.pptx) | `touying compile --format pptx` |
| Export to a self-contained HTML deck | `touying compile --format html` |
| Live-preview while editing | Tinymist's *Typst Preview* (VS Code) |
| Present from a dual-screen laptop | `pdfpc` or `pympress` |
| Share a deck via GitHub URL | `gistd.myriad-dreamin.com` |
