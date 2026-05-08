# Integration — Pinit

> Source: <https://touying-typ.github.io/docs/integration/pinit>
>
> Package: [`pinit`](https://github.com/OrangeX4/typst-pinit/) v0.2.2

[Pinit](https://github.com/OrangeX4/typst-pinit/) provides **absolute
positioning relative to the page** plus **relative positioning relative
to "pins"** — perfect for callouts, arrows, highlights, and explanatory
labels in slides.

## Simple example

```typst
#import "@preview/pinit:0.2.2": *
#set text(size: 24pt)

A simple #pin(1)highlighted text#pin(2).

#pinit-highlight(1, 2)
#pinit-point-from(2)[It is simple.]
```

`#pin(<id>)` drops a pin at the current position. `<id>` may be an
integer or a string. Pinit functions then reference these pins.

| Function | Effect |
| -------- | ------ |
| `#pin(<id>)` | Drop a pin (no visible output). |
| `#pinit-highlight(<from>, <to>, ...)` | Yellow highlight rect from `<from>` to `<to>`. |
| `#pinit-point-from(<pin>)[label]` | Arrow + label pointing **from** the pin. |
| `#pinit-point-to(<pin>, fill: ..., body)` | Arrow + label pointing **to** the pin. |
| `#pinit-rect(<from>, <to>)` | Rectangle bounding the area between two pins. |
| `#pinit-line(stroke: ..., 1, 2)` | Line connecting two pins. |
| `#pinit-place(<pin>, dx: ..., dy: ...)[body]` | Absolute place body relative to the pin. |

## Complex example

The full `Asymptotic Notation` example uses `default-theme`, paragraph
styling, custom helpers (`#crimson`, `#redbold`, `#blueit`,
`#greybox`), and a long sequence of `#pause` reveals interleaved with
pinit calls:

```typst
#import "@preview/touying:0.7.3": *
#import themes.default: *
#import "@preview/pinit:0.2.2": *

#set text(size: 20pt, font: "Calibri", ligatures: false)
#show heading: set text(weight: "regular")
#show heading: set block(above: 1.4em, below: 1em)
#show heading.where(level: 1): set text(size: 1.5em)

#let crimson = rgb("#c00000")
#let greybox(..args, body) = rect(
  fill: luma(95%), stroke: 0.5pt,
  inset: 0pt, outset: 10pt, ..args, body,
)
#let redbold(body) = { set text(fill: crimson, weight: "bold"); body }
#let blueit(body)  = { set text(fill: blue); body }

#show: default-theme.with(aspect-ratio: "4-3")

#slide[
  = Asymptotic Notation: $O$
  Use #pin("h1")asymptotic notations#pin("h2") to describe asymptotic efficiency of algorithms.

  #pause
  #greybox[
    Given a function $g(n)$, we denote by $O(g(n))$ the following *set of functions*:
    #redbold(${f(n): "exists" c > 0 "and" n_0 > 0,
              "such that" f(n) <= c dot g(n) "for all" n >= n_0}$)
  ]
  #pinit-highlight("h1", "h2")

  #pause
  $f(n) = O(g(n))$: #pin(1)$f(n)$ is *asymptotically smaller* than $g(n)$.#pin(2)
  #only("4-", pinit-line(stroke: 3pt + crimson,
                          start-dy: -0.25em, end-dy: -0.25em, 1, 2))

  #pause
  #block[Insertion Sort #pin("r1")example#pin("r2"):]
  - Best case:  $T(n) approx c n + c' n - c''$ #pin(3)
  - Worst case: $T(n) approx c n + (c' / 2) n^2 - c''$ #pin(4)
  #pinit-rect("r1", "r2")

  #pause
  #pinit-place(3, dx: 15pt, dy: -15pt)[#redbold[$T(n) = O(n)$]]
  #pinit-place(4, dx: 15pt, dy: -15pt)[#redbold[$T(n) = O(n^2)$]]

  #pause
  #blueit[Q: Is $n^3 = O(n^2)$#pin("que")? How to prove#pin("ans")?]

  #pause
  #pinit-point-to("que", fill: crimson, redbold[No.])
  #pinit-point-from("ans", body-dx: -150pt)[
    Show that $(3/2)^n >= c$ has infinitely many solutions for $n$.
  ]
]
```

## Example

See [`examples/01-pinit/01-pinit.typ`](./examples/01-pinit/01-pinit.typ).

## Pitfalls

- Pin IDs are *positional* — `#pin(1)` and `#pin(2)` must be **before**
  the pinit-* call that references them. Forward references will panic.
- `#pinit-line(start-dy: ..., end-dy: ...)` is the right tool for fine-
  tuning vertical alignment when text-baseline pins are in use.
- For a slide with many pins, prefer **string** IDs (`"h1"`, `"r1"`)
  over integers — easier to read and reorder.
