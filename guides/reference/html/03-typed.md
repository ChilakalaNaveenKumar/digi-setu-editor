# Typed HTML – `html.<tag>(...)` Functions

The `html` module provides a **typed wrapper** around
[`html.elem`](./01-elem.md) — one Typst function per HTML element,
with attributes exposed as named parameters. Typst types
(strings, booleans, integers, lengths, arrays, ...) are automatically
converted to the right HTML attribute strings.

```typst
#html.video(
  controls: true,
  width: 1280,
  height: 720,
  src: "sunrise.mp4",
)[
  Your browser does not support the video tag.
]
```

This is equivalent to:

```typst
#html.elem("video", attrs: (
  controls: true,
  width: "1280",
  height: "720",
  src: "sunrise.mp4",
))[Your browser does not support the video tag.]
```

…but with autocomplete, parameter docs, and type-checking.

## Coverage

`html.typed` exposes the full HTML element catalog, including:

- **Document structure:** `html.html`, `html.head`, `html.body`,
  `html.title`, `html.meta`, `html.link`, `html.script`, `html.style`.
- **Sectioning:** `html.section`, `html.article`, `html.nav`,
  `html.aside`, `html.header`, `html.footer`, `html.main`,
  `html.address`.
- **Headings:** `html.h1` … `html.h6`, `html.hgroup`.
- **Text grouping:** `html.p`, `html.pre`, `html.blockquote`,
  `html.figure`, `html.figcaption`.
- **Inline:** `html.a`, `html.strong`, `html.em`, `html.code`,
  `html.kbd`, `html.samp`, `html.var`, `html.mark`, `html.span`,
  `html.br`, `html.wbr`, `html.abbr`, `html.cite`, `html.q`,
  `html.time`, `html.data`.
- **Lists:** `html.ul`, `html.ol`, `html.li`, `html.dl`, `html.dt`,
  `html.dd`.
- **Embedded content:** `html.img`, `html.audio`, `html.video`,
  `html.source`, `html.track`, `html.iframe`, `html.embed`,
  `html.object`, `html.picture`.
- **Tables:** `html.table`, `html.thead`, `html.tbody`, `html.tfoot`,
  `html.tr`, `html.th`, `html.td`, `html.caption`, `html.col`,
  `html.colgroup`.
- **Forms:** `html.form`, `html.input`, `html.textarea`,
  `html.button`, `html.select`, `html.option`, `html.optgroup`,
  `html.label`, `html.fieldset`, `html.legend`, `html.datalist`,
  `html.output`, `html.progress`, `html.meter`.
- **Interactive:** `html.details`, `html.summary`, `html.dialog`,
  `html.menu`.
- **Scripting:** `html.canvas`, `html.template`, `html.slot`.
- **Semantic editing markers:** `html.ins`, `html.del`.
- **Ruby and Asian text:** `html.ruby`, `html.rt`, `html.rp`,
  `html.rb`, `html.rtc`.
- **Other:** `html.hr`, `html.dfn`, `html.b`, `html.i`, `html.s`,
  `html.u`, `html.small`, `html.sub`, `html.sup`.

Each function takes its element-specific attributes as named
parameters plus a positional `body` (omit for void elements like
`html.img`, `html.meta`, `html.input`).

## Global attributes

Some attributes are common to every element (HTML *global
attributes*) — they're available on every typed function. The most
important ones:

| Attribute        | Type           | Notes                                       |
| ---------------- | -------------- | ------------------------------------------- |
| `id`             | str            | Element id.                                 |
| `class`          | str / array of str | One or more class names.                |
| `style`          | str            | Inline CSS.                                 |
| `lang`           | str            | Language code.                              |
| `dir`            | `"ltr"` / `"rtl"` / `"auto"` | Text direction.                |
| `title`          | str            | Tooltip / advisory text.                    |
| `tabindex`       | int            | Tab focus order.                            |
| `hidden`         | bool / str     | Hide from rendering.                        |
| `accesskey`      | str            | Keyboard shortcut.                          |
| `contenteditable`| bool / str     | Allow inline editing.                       |
| `draggable`      | bool / `"true"`/`"false"` | Drag-and-drop hint.              |
| `role`           | str            | ARIA role.                                  |
| `aria-*`         | str            | ARIA attributes (typed where common).       |
| `data-*`         | dictionary `data: (...)` | Custom `data-*` attributes.       |

Custom attributes (any prefix) can also be passed via `attrs: (...)`
on the underlying `html.elem` if you can't reach them via a typed
parameter.

## Recipes

### Typed nav block

```typst
#html.nav(aria-label: "Site navigation", [
  #html.ul([
    #html.li([#link("/")[Home]])
    #html.li([#link("/blog/")[Blog]])
  ])
])
```

### Embedded video with fallback

```typst
#html.video(controls: true, width: 640, height: 360, [
  #html.source(src: "talk.webm", type: "video/webm")
  #html.source(src: "talk.mp4",  type: "video/mp4")
  #html.p[Your browser does not support video. #link("talk.mp4")[Download]]
])
```

### Form with semantic labels

```typst
#html.form(action: "/subscribe", method: "post", [
  #html.label(for: "email")[Your email]
  #html.input(type: "email", id: "email", name: "email", required: true)
  #html.button(type: "submit")[Subscribe]
])
```

### Custom data attributes

```typst
#html.div(
  class: "card",
  data: (id: "42", category: "review"),
  [Some content]
)
// → <div class="card" data-id="42" data-category="review">…</div>
```

## When to reach for `html.elem` instead

- The element you want isn't in the typed catalog.
- You want a **custom non-standard tag** (Web Components,
  `<my-element>`).
- You're code-generating HTML where the tag and/or attributes are
  computed at runtime.

## Pairing with target branching

Same as `html.elem` — wrap typed calls in `if target() == "html"`
when you only want them in HTML output:

```typst
#if target() == "html" {
  html.aside(class: "callout", [Web-only sidebar.])
}
```

For an exhaustive per-element parameter list, see the official
[Typed HTML reference](https://typst.app/docs/reference/html/typed/).
