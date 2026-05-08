# `link` — hyperlinks (URLs and internal jumps)

`link(dest, body) -> content`

Creates a hyperlink. **By default, links look identical to surrounding text** — apply a `show link: ...` rule to make them visually distinct.

## Destination types

| `dest` form                         | Behavior                                                    |
| ----------------------------------- | ----------------------------------------------------------- |
| `"https://..."` / `"http://..."`    | URL                                                         |
| `"mailto:foo@bar.com"`              | mailto; if `body` omitted, the address (without `mailto:`) is used |
| `"tel:+15551234567"`                | tel; same body-defaulting rule                              |
| `<label>`                           | jump to the labeled element                                 |
| `location` value                    | from `here()` / `locate()` / `query()`                      |
| `(page: int, x: length, y: length)` | absolute page-coordinate jump (1-indexed page; coords from page top-left) |

## Markup shorthand

Bare URLs starting with `http://` or `https://` in markup are **automatically** wrapped in `link(...)`. You only need `#link(...)` explicitly when:

- the URL doesn't start with `http(s)://` (mailto, tel, file)
- you want a **different visible body** than the URL itself
- you're targeting a label, location, or page-coords

## Hyphenation

Links **disable hyphenation by default** to keep URLs intact across line breaks. To opt in:

```typst
#show link: set text(hyphenate: true)
```

## Common patterns

```typst
// Underline every link
#show link: underline

// Color URLs but not internal jumps (URLs are always strings)
#show link: it => if type(it.dest) == str { text(fill: blue, it) } else { it }

// Make labels referenceable as anchors AND linkable as plain links
= My Section <my-section>
Jump to #link(<my-section>)[my section] — same target, no auto-text.
```

## Accessibility / PDF

In PDF export, every link gets an auto-generated tooltip:

- URLs → the URL itself
- Internal jumps → no tooltip; the visible body is what the user sees

In HTML export, internal jumps become anchor fragment links. Typst auto-generates element IDs from labels when the label characters are CSS-friendly (alphanumerics, `-`, `_`, no leading digit). Otherwise it falls back to `loc-N` IDs.

## `link` vs `ref`

- **`link(<label>)[Some text]`** — manual body, no automatic prefix like "Section 3.2".
- **`ref(<label>)`** — automatic text based on the target (e.g. "Section 3.2", "Figure 1"). For labeled headings/figures, prefer `ref` unless you specifically want custom anchor text.

## Pitfalls

- **The body is required for non-URL destinations.** `link(<intro>)` with no body errors; provide a content body or use `ref(<intro>)` instead.
- **Page-coords are unforgiving.** `(page: 1, x: 0pt, y: 0pt)` is the absolute top-left — pages are physical, not logical. Layout shifts can make the target jump look "wrong".
- **`mailto:` / `tel:` URL-encoding** is your responsibility. Spaces and special chars must be percent-encoded.
- **Default invisibility** is the #1 newbie surprise. Add `#show link: underline` early in any document with internal links.

## Examples (compile-verified)

- `examples/09-link/01-link-destinations.typ` — every `dest` shape (URL auto + explicit, mailto, tel, label, page coords), `#show link: underline`.

## Reference

- Official: https://typst.app/docs/reference/model/link/
- `ref` (auto-text refs): https://typst.app/docs/reference/model/ref/
- `here` / `locate` / `query`: https://typst.app/docs/reference/introspection/
