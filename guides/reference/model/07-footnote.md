# `footnote` — superscript notes at the bottom of the page

`footnote(body: label | content, numbering: str | function = "1") -> content`

Inserts a superscript marker that links to a note at the bottom of the same page. Notes auto-number sequentially throughout the document and break across pages.

```typst
Check the docs for more details.#footnote[https://typst.app/docs]
```

## Two body forms

| `body` type | Behaviour                                                                                |
| ----------- | ---------------------------------------------------------------------------------------- |
| `content`   | Creates a NEW footnote with `body` at the bottom.                                        |
| `label`     | Creates a marker that points to the EXISTING labelled footnote — no new entry rendered. |

So, to reuse one footnote in three places:

```typst
First reference#footnote[The note] <fn>
Second reference @fn
Third reference #footnote(<fn>)
```

## Marker placement

The marker **attaches to the preceding word** even if there is whitespace before `#footnote(...)` in the source. To preserve a space, use a literal `#" "` or `#h(0.5em)`:

```typst
text#footnote[no space here]
text #footnote[also no space here]   // collapses!
text#h(0.5em)#footnote[forced space]
```

## Per-document marker style

Set rules on `footnote` change the marker numbering everywhere:

```typst
#set footnote(numbering: "*")  // *, †, ‡, §, ¶, ‖, then doubled
```

For per-page reset, manually update the `counter(footnote)` in the page header (a future API may simplify this).

## `footnote.entry` — the listing at the bottom

Configures the per-page listing. Set rules **must come before any page content** (entry properties must be uniform per page run).

| Field        | Default                                | Purpose                                |
| ------------ | -------------------------------------- | -------------------------------------- |
| `separator`  | `line(length: 30% + 0pt, stroke: 0.5pt)` | Divider above the listing            |
| `clearance`  | `1em`                                  | Space between body and separator       |
| `gap`        | `0.5em`                                | Space between consecutive entries      |
| `indent`     | `1em`                                  | Per-entry left indent                  |

`#show footnote.entry: it => ...` gives full control over how each entry renders. Inside the handler, `it.note` is the original `footnote` element; `it.note.location()` lets you pull the counter state.

## Pitfalls

- **Set/show rules in the calling scope may not apply to footnote BODY content.** Footnotes get composed at a different layout phase. If your fancy rules don't show up inside the footnote body, that's why — apply them globally (top of file).
- **`footnote.entry` set rules must be at the top of the document** (before any rendered content). Placing them later in the doc errors with the "uniform per page run" diagnostic.
- **Markers stick to the previous word.** That includes through trailing whitespace. Force a gap with `#" "` or `#h(...)`.
- **Reusing a footnote with `<fn>` doesn't repeat the body.** Only the marker recurs; the entry at the bottom is still rendered once.
- **Don't put block-level content in a footnote body.** Footnotes are inline contexts; bigger structures (figures, tables) belong in the main flow.

## Examples (compile-verified)

- `examples/07-footnote/01-footnote-basics.typ` — basic markers, forced spacing, label form for repeat references, `numbering: "*"`.
- `examples/07-footnote/02-customize-entries.typ` — `footnote.entry` set rule + `#show footnote.entry:` for fully custom per-entry rendering.

## Reference

- Official: https://typst.app/docs/reference/model/footnote/
- `super` (the marker is a regular superscript): https://typst.app/docs/reference/text/super/
- `counter`: https://typst.app/docs/reference/introspection/counter/
