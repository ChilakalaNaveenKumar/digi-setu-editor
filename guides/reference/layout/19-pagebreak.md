# `pagebreak(weak: false, to: none)` — manual page break

Forces the following content to start on a new page. **Cannot** be used inside containers (`block`, `box`, etc.) — it operates at the document level only.

## Parameters

| Param  | Type                  | Default  | Notes                                                          |
| ------ | --------------------- | -------- | -------------------------------------------------------------- |
| `weak` | bool                   | `false`   | Skip the break if the current page is already empty.            |
| `to`   | `none` / `"even"` / `"odd"` | `none`    | Force the next page to be of the given parity (insert blank if needed). |

## Widows and orphans

Even without manual `pagebreak()`, automatic pagination tries to **avoid widows and orphans** (single lines stranded at the top or bottom of a page). To disable that behaviour, tweak `text.costs` (see the [text reference](../text/12-text.md)).

## Common patterns

| Goal                                                | Recipe                              |
| --------------------------------------------------- | ----------------------------------- |
| End the current page now                             | `#pagebreak()`                       |
| Force an odd-page start (book chapters)             | `#pagebreak(to: "odd")`              |
| Don't break if already on a fresh page              | `#pagebreak(weak: true)`             |

## Related

- [`set page(...)`](./18-page.md) — change page properties at a pagebreak boundary.
- [`colbreak()`](./06-colbreak.md) — column break (page break in single-column layouts).

## Examples (compile-verified)

- `examples/19-pagebreak/01-pagebreak.typ` — basic pagebreak, `to: "odd"` forced parity, `weak: true` collapse demonstration.

## Reference

https://typst.app/docs/reference/layout/pagebreak/
