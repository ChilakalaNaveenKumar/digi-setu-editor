# 04 — Settings and Config

> Source: <https://touying-typ.github.io/docs/tutorials/settings>

## Global styles

For Touying, *global styles* are `set` / `show` rules that apply
everywhere — `#set text(size: 20pt)`, `#set par(justify: true)`, etc.

Themes encapsulate their own global styles via `config-methods(init: ...)`:

```typst
config-methods(
  init: (self: none, body) => {
    set text(fill: self.colors.neutral-darkest, size: 25pt)
    show footnote.entry: set text(size: .6em)
    show strong: self.methods.alert.with(self: self)
    show heading.where(level: self.slide-level + 1): set text(1.4em)
    body
  },
)
```

If you want to add your own global styles, place them **before or after**
the theme show rule. For instance the `metropolis` theme recommends:

```typst
#set text(font: "Fira Sans", weight: "light", size: 20pt)
#show math.equation: set text(font: "Fira Math")
#set strong(delta: 100)
#set par(justify: true)
```

## Global information — `config-info`

Use `config-info` to record presentation metadata. Themes read it via
`self.info.<field>`:

```typst
config-info(
  title: [Title],
  subtitle: [Subtitle],
  author: [Authors],
  date: datetime.today(),
  institution: [Institution],
  contact: [contact\@mail.com],
  logo: [logo.png],
  extra: (supervisor: [Supervisor],),
)
```

`extra:` lets you stash arbitrary fields — read them as
`self.info.extra.supervisor`.

The `date:` field accepts `datetime` (formatted via
`config-common(datetime-format: "[year]-[month]-[day]")`) or `content`.

## Preamble — `config-common(preamble: ...)`

Code that must run on **every** slide goes in the preamble. Common case:
initialising `codly` syntax highlighting:

```typst
#show: simple-theme.with(
  config-common(preamble: {
    codly(languages: codly-languages)
  }),
)
```

## Show-rule config overrides — `touying-set-config`

Override any config for the current slide and all subsequent slides:

```typst
== Blue Background Slide
#show: touying-set-config.with(config-page(fill: blue.lighten(80%)))
This slide has a blue background.

== Red Accent Slide
#show: touying-set-config.with(config-colors(primary: red))
#alert[Alert with red accent.]

== Changed Cover
#show: touying-set-config.with(config-methods(
  cover: utils.semi-transparent-cover,
))
Initial. #pause Now with semi-transparent cover.
```

## Local config overrides — `slide(config: ...)`

To affect a single slide only, pass `config:` directly:

```typst
== Local Config
#slide(config: config-page(fill: purple.lighten(90%)))[
  Only this slide has a purple background.
]
```

## Deferred config show rules

`defer: true` postpones the change until the **next** slide. This is
how `#show: appendix` works under the hood:

```typst
== Content Slide
Some content.
#show: touying-set-config.with(defer: true, config-common(appendix: true))
// equivalent: `show: appendix`
== Appendix
Counter no longer increases.
```

## Frozen counters

When a slide animates, figure / theorem counters increment per-subslide by
default. Freeze them:

```typst
config-common(frozen-counters: (figure.where(kind: image),))
// or, for theorion:
config-common(frozen-counters: (theorem-counter,))
```

## Querying config — `touying-get-config`

`touying-get-config` is evaluated at `context` time and returns content.

```typst
// Whole config dict (then dictionary access)
#touying-get-config().info.author
#touying-get-config().common.handout
#touying-get-config().handout       // common is also at top level

// Dot-separated string key
#touying-get-config("info.author")
#touying-get-config("info")          // entire info sub-dict

// Default value (avoids panic on missing keys)
#touying-get-config("random.dict.value", default: "fallback")

// Custom config set via touying-set-config
#show: touying-set-config.with((random: (dict: (value: 123))))
#touying-get-config("random.dict.value")  // displays "123"
```

> **Warning.** When accessing custom config, **always use the string-key
> form** `touying-get-config("random.dict.value")`. The chained form
> `touying-get-config("random.dict").value` tries to access `.value` on
> a content element and fails.

## Example

See [`examples/04-settings/04-settings.typ`](./examples/04-settings/04-settings.typ).

## Pitfalls

- `config-common(...)` keys are *common* across themes (e.g. `handout`,
  `slide-level`, `preamble`, `frozen-counters`). `config-page(...)` is for
  page-level keys (`fill`, `header`, `footer`, `margin`, …).
- `touying-set-config` with `defer: false` (default) applies to the
  current slide; with `defer: true` to the next.
- `config-info(extra: (...))` is the recommended escape hatch for arbitrary
  metadata themes don't know about.
