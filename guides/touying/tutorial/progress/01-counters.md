# Progress 01 — Slide Counters and Progress

> Source: <https://touying-typ.github.io/docs/tutorials/progress/counters>

## `utils.slide-counter`

`utils.slide-counter` is the primary Typst counter that increments on
every slide. Display it inside a `context` expression:

```typst
#context utils.slide-counter.display()
```

In a custom footer:

```typst
#import "@preview/touying:0.7.3": *
#import themes.default: *

#show: default-theme.with(
  aspect-ratio: "16-9",
  config-page(
    footer: context [Slide #utils.slide-counter.display()],
  ),
)
```

## `utils.last-slide-number`

`utils.last-slide-number` is the *number of the last slide before the
appendix* — the denominator you want for "Slide X of Y":

```typst
#context utils.slide-counter.display() + " / " + utils.last-slide-number
```

This is what the `simple`, `metropolis`, `university`, `dewdrop`, and
`stargazer` themes put in the bottom-right corner.

## `utils.touying-progress`

`utils.touying-progress(ratio => ...)` runs a callback with a `ratio`
between 0.0 and 1.0 indicating how far through the deck you are:

```typst
#utils.touying-progress(ratio => {
  box(width: ratio * 100%, height: 4pt, fill: primary)
})
```

This is exactly how the `metropolis` and `aqua` themes draw their
top-of-page progress bar.

## `#show: appendix`

`appendix` is a show rule that **stops** the slide counter — appendix
slides do not affect the total shown in the footer:

```typst
= Main Section
== Introduction
The slide count increments normally here.
== Second Slide
Still counting.

#show: appendix

= Appendix
== Backup Slide
The footer still shows the count from the last main slide.
```

Internally, `appendix` is `touying-set-config.with(defer: true,
config-common(appendix: true))` — see the *Deferred Config Show Rules*
section in [`../04-settings.md`](../04-settings.md).

## Example

See [`examples/01-counters/01-counters.typ`](./examples/01-counters/01-counters.typ).

## Pitfalls

- Always wrap `utils.slide-counter.display()` in `#context` — Typst
  counters are evaluated in context.
- `utils.last-slide-number` is a content value (no `display()` needed).
- `#show: appendix` must come **after** the main content but **before**
  the first appendix heading.
