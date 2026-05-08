# `html.elem` – Raw HTML Element with Typst Body

```typst
html.elem(
  tag: str,                              // required
  attrs: dictionary = (:),               // HTML attributes
  body: none | content = none,           // inner content
) -> content
```

Emit an HTML element with an arbitrary tag and attribute set. The
body can be **arbitrary Typst content** — including more `html.elem`
calls, regular markup, math, etc. Typst recursively serializes the
body to HTML.

## Behavior

- The function only takes effect when exporting to HTML; in PDF/SVG/PNG
  output it has no effect (you'll see the body or nothing,
  depending on `target()`).
- Typst will **omit its own `<html>`, `<head>`, `<body>`** wrappers
  if you create them yourself with `html.elem(...)`. Useful when you
  want full control of the page chrome.
- Typst checks that the (`tag`, `attrs`) combination is **valid
  HTML syntax**. Some tags (e.g. `meta`, `link`, `img`) are
  *void elements* and cannot have a body. Others have required
  attributes.

## Parameters

| Name    | Type           | Required | Default  | Notes                                       |
| ------- | -------------- | -------- | -------- | ------------------------------------------- |
| `tag`   | str            | yes      | —        | The element tag (`"div"`, `"section"`, ...). |
| `attrs` | dictionary     | no       | `(:)`    | Attribute name → value pairs.               |
| `body`  | none / content | no       | `none`   | Inner content; recursively serialized.      |

`attrs` values can be strings, booleans, numbers, etc. — they're
converted to attribute strings the same way the typed module does.

## Recipes

### Wrap each "article" in a `<article>`

```typst
#let article(body) = html.elem("article", attrs: (class: "card"), body)

#article[
  = First post
  Hello, world!
]
```

### Add ARIA / semantics

```typst
#html.elem("nav", attrs: (
  "aria-label": "Site navigation",
), [
  - #link("/")[Home]
  - #link("/blog/")[Blog]
])
```

### Inline a comment / footnote / aside

```typst
#html.elem("aside", attrs: (class: "footnote"), body: [
  This shows up only in HTML; in PDF, use #footnote[...].
])
```

### Branch by target

The most common pattern. Same source, two emit shapes:

```typst
#let card(body) = if target() == "html" {
  html.elem("section", attrs: (class: "card"), body)
} else {
  block(stroke: 0.5pt, inset: 8pt, body)
}
```

### Build a custom `<head>`

If you call `html.elem("html", ...)` (or `head`/`body`), Typst will
not auto-emit its own boilerplate — you control the entire structure:

```typst
#html.elem("html", attrs: (lang: "en"), [
  #html.elem("head", [
    #html.elem("meta", attrs: (charset: "utf-8"))
    #html.elem("title", "My document")
  ])
  #html.elem("body", [
    = Hello!
  ])
])
```

## Pairing with `html.typed`

Most of the time you don't need to remember the exact tag/attribute
spelling — use [`html.typed`](./03-typed.md) which exposes every
HTML element as a typed Typst function (`html.section`, `html.nav`,
`html.video(controls: true, src: "...")`). `html.elem` is the
escape hatch when:

- You want a tag the typed module doesn't yet expose.
- You want a custom attribute (`data-*`, `aria-*`, vendor-specific).
- You're code-generating HTML and the tag/attrs are dynamic.
