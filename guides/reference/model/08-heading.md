# `heading` — section heading

`heading(body: content, level: auto | int, depth: int = 1, offset: int = 0, numbering: none | str | function = none, supplement: ?, outlined: bool = true, bookmarked: auto | bool = auto, hanging-indent: auto | length = auto) -> content`

A logical section. Levels start at 1 and are unbounded upwards. **Do not use a level-1 heading for the document title** — use the `title` element. A level-1 heading is a top-level *section*.

## Markup shorthand

```typst
= Section
== Subsection
=== Sub-sub
```

`N` equals signs followed by a space → `depth = N`. The shorthand sets `depth`, not `level` — the actual level is `level = offset + depth`.

## Numbering

`numbering: "1."`, `numbering: "1.a)"`, or any pattern/function (see [`numbering`](./11-numbering.md)). Default `none` (unnumbered).

```typst
#set heading(numbering: "1.a)")
= First            // 1)
== Sub             // 1.a)
== Another sub     // 1.b)
= Second           // 2)
```

Why level 1 prints `1)` and not `1.`: in the pattern, `.` is the **prefix** for the counting symbol `a`, not for `1`. At depth 1, `a` isn't used, so the `.` doesn't appear. The trailing `)` is the **suffix** (everything after the last counting symbol) and is appended to every rendered number.

## Key fields

| Field            | Default | What it does                                                     |
| ---------------- | ------- | ---------------------------------------------------------------- |
| `level`          | `auto`  | Absolute level. `auto` = `offset + depth`.                       |
| `depth`          | `1`     | Relative nesting (set by `=` count in markup).                    |
| `offset`         | `0`     | Added to depth to get level. Useful when nesting sub-documents.   |
| `numbering`      | `none`  | Pattern string OR function.                                      |
| `supplement`     | `auto`  | Word used by `#ref` (e.g. `[Chapter]`).                          |
| `outlined`       | `true`  | Show in `#outline()` (and in PDF bookmarks by default).          |
| `bookmarked`     | `auto`  | Independent PDF-bookmark control. `auto` mirrors `outlined`.     |
| `hanging-indent` | `auto`  | Indent for wrapped lines; `auto` uses numbering width.            |

## Accessibility

**Do not skip levels.** From a level-3 heading, the next must be 1, 2, 3, or 4 — never 5+. Screen readers rely on the hierarchy.

## HTML export

| Element              | HTML tag |
| -------------------- | -------- |
| `title`              | `<h1>`   |
| Level-1 heading      | `<h2>`   |
| Level-2 heading      | `<h3>`   |
| ... (level + 1)      | ...      |

## Show rules

Common pattern — restyle by level:

```typst
#show heading.where(level: 1): set text(fill: navy)
#show heading.where(level: 1): it => block(above: 1.4em, below: 0.6em, it)
```

When you build a fully custom heading, **wrap the body in a `block`** to keep the implicit "sticky" behaviour (prevents orphans at the bottom of a page).

## Pitfalls

- **Level-1 heading ≠ title.** Use `#title()` for the document title; a level-1 heading is a top-level section.
- **Skipping levels breaks AT.** Don't go `=` then `===`.
- **Custom show rules can orphan headings.** Always wrap in `block(...)` if you replace the default body layout.
- **Markup needs the trailing space.** `=Foo` (no space) is just literal text, not a heading.
- **`set heading(offset: ...)` shifts everything below.** Reset it explicitly if you only want to shift one section.

## Examples (compile-verified)

- `examples/08-heading/01-syntax-and-numbering.typ` — `=`/`==`/`===` markup with `numbering: "1.a)"`.
- `examples/08-heading/02-offset-and-outlined.typ` — `offset` shifting depth, `outlined: false` to hide a heading from the outline.
- `examples/08-heading/03-show-rule-and-where.typ` — `#show heading.where(level: 1)` and `level: 2` rules with body wrapping.

## Reference

- Official: https://typst.app/docs/reference/model/heading/
- `title`: https://typst.app/docs/reference/model/title/
- `numbering`: https://typst.app/docs/reference/model/numbering/
- `outline`: https://typst.app/docs/reference/model/outline/
