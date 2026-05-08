# `page(...)` — page setup

Configures the page itself. Almost always used as `set page(...)`. Each `set page` rule introduces a **page run** — a contiguous sequence of pages with the same page properties — that ends at the next pagebreak.

Refer to the [Guide for Page Setup](https://typst.app/docs/guides/page-setup/) for an end-to-end example.

## Most-used parameters

| Param            | Type                                      | Default            | Notes                                                          |
| ---------------- | ----------------------------------------- | ------------------ | -------------------------------------------------------------- |
| `paper`           | str                                        | `"a4"`              | Standard size shorthand for `width` and `height`.              |
| `width`           | `auto` / length                            | `595.28pt`          | Page width. `auto` = grow to fit content.                      |
| `height`          | `auto` / length                            | `841.89pt`          | Page height. `auto` = no auto pagebreaks (only manual).        |
| `flipped`         | bool                                       | `false`             | Landscape orientation.                                          |
| `margin`          | `auto` / relative / dictionary             | `auto`              | Per-side dictionary supported (`top`, `right`, `bottom`, `left`, `inside`, `outside`, `x`, `y`, `rest`). |
| `binding`         | `auto` / alignment                         | `auto`              | Affects `inside`/`outside` margins. `auto` follows text direction. |
| `columns`         | int                                        | `1`                 | Page-level columns (real pagebreaks/footnotes work).            |
| `fill`            | `none` / `auto` / color / gradient / tiling | `auto`              | Background. `auto` = none in PDF, white in PNG/SVG.             |
| `numbering`       | `none` / str / function                    | `none`              | Same syntax as [`numbering()`](../model/11-numbering.md). Patterns may take 1 or 2 numbers (current, total). |
| `number-align`    | alignment                                   | `center + bottom`   | `top`/`bottom` placement. Horizon forbidden.                  |
| `supplement`      | `none` / `auto` / content                  | `auto`              | Word prepended in page references.                             |
| `header` / `footer` | `none` / `auto` / content                | `auto`              | Page header / footer. `auto` shows numbering if appropriate.   |
| `header-ascent`   | relative                                    | `30%`               | How far the header rises into the top margin.                  |
| `footer-descent`  | relative                                    | `30%`               | How far the footer descends into the bottom margin.            |
| `background` / `foreground` | `none` / content                | `none`              | Behind / over the body. Common for watermarks.                  |

## Standard paper sizes (selection)

`"a4"` (default), `"a3"`, `"a5"`, `"a6"`, `"us-letter"`, `"us-legal"`, `"us-tabloid"`, `"us-executive"`, `"presentation-16-9"`, `"presentation-4-3"`, plus many ISO/JIS/ANSI/ARCH/SAC/business-card variants. See the [official paper-size list](https://typst.app/docs/reference/layout/page/#parameters-paper).

## Page-level columns

```typst
#set page(columns: 2)
```

Use this instead of `#columns(2)[...]` when you need columns across the **whole document** — pagebreaks, footnotes, and line numbering all keep working.

## Numbering with one or two numbers

| Pattern | Renders                  |
| ------- | ------------------------ |
| `"1"`    | `1`, `2`, ...            |
| `"1 / 1"`| `1 / 12`, `2 / 12`, ...   |
| `"i"`    | `i`, `ii`, `iii`, ...    |

Pass a function for full control: `numbering: (n, total) => [Page #n of #total]`.

## Background watermark

```typst
#set page(background: rotate(24deg,
  text(48pt, fill: rgb("FFCBC4"))[*CONFIDENTIAL*]
))
```

## Accessibility

Headers, footers, foregrounds, and backgrounds are **not read by AT**. Don't put critical content there.

## Examples (compile-verified)

- `examples/18-page/01-page-basics.typ` — A5 paper, custom margins, numbering, custom header with `h(1fr)`, watermark via background.
- `examples/18-page/02-page-columns-and-references.typ` — page-level columns, custom `supplement`, page-form ref.

## Reference

https://typst.app/docs/reference/layout/page/
