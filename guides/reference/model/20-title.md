# `title` — visible document title (≤ 1 per document)

`title(body: auto | content = auto) -> content`

Renders the **main title** of the whole document on the page. Distinct from level-1 headings, which are *sections* of the document.

```typst
#set document(title: [Interstellar Mail Delivery])
#title()

= Introduction
...
```

## Two ways to populate it

| Form                              | Behaviour                                                       |
| --------------------------------- | --------------------------------------------------------------- |
| `#title[My Paper]`                | Inline body wins; `document.title` is **unaffected**.           |
| `#title()` *(or `#title(auto)`)* | Falls back to `document.title`. **Errors** if not set.          |

The fallback form is the **preferred** pattern when you want the same string in both the visible title AND PDF metadata — set it once in `document` and reference it via `#title()`.

## Where titles differ from headings

| Aspect                | `title`                          | `= Heading` (level 1)            |
| --------------------- | -------------------------------- | -------------------------------- |
| Per document          | At most one                      | Many                             |
| Semantic role         | Document title                   | Top-level section                |
| HTML export           | `<h1>`                           | `<h2>`                           |
| Counts as outline?    | No                               | Yes (by default)                 |
| Numbered?             | No                               | Yes if `set heading(numbering:)` |

## Frontmatter rule

Author lists, dates, abstracts, etc. **do not belong inside the title body**. Place them as their own elements (paragraphs, blocks, custom layout) immediately after `#title()`.

## Pitfalls

- **`#title()` with no preceding `#set document(title: ...)` errors.** Either pass a body or set the document title first.
- **Don't substitute `= Heading` for a title.** It changes semantics (top-level section vs. document title) and HTML/PDF tagging.
- **Title content is not what PDF viewers show.** That's `document.title` — they're related but separate. The visible content of `title[...]` is for the printed page; the PDF tab name is whatever you `set document(title: [...])`.
- **Show rules.** `#show title: ...` works like any element show rule and lets you apply custom styling globally without changing call sites.

## Examples (compile-verified)

- `examples/20-title/01-title-default-and-override.typ` — `auto` fallback to `document.title`, inline override, and contrast with a level-1 heading.

## Reference

- Official: https://typst.app/docs/reference/model/title/
- `document` (PDF metadata): https://typst.app/docs/reference/model/document/
- `heading` (sections): https://typst.app/docs/reference/model/heading/
