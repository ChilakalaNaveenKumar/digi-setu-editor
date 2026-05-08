# Integration — MiTeX

> Source: <https://touying-typ.github.io/docs/integration/mitex>
>
> Package: [`mitex`](https://github.com/mitex-rs/mitex) v0.2.6

When you already have a LaTeX equation that you don't want to rewrite as
Typst math, use [MiTeX](https://github.com/mitex-rs/mitex). It compiles
LaTeX math into Typst.

## Basic usage

```typst
#import "@preview/mitex:0.2.6": *

Write inline equations like #mi("x") or #mi[y].

Block equations also work (this case is from
#text(blue.lighten(20%), link("https://katex.org/")[katex.org])):

#mitex(`
  \newcommand{\f}[2]{#1f(#2)}
  \f\relax{x} = \int_{-\infty}^\infty
    \f\hat\xi\,e^{2 \pi i \xi x}
    \,d\xi
`)
```

| Function | Use |
| -------- | --- |
| `#mi("x")` / `#mi[x]` | Inline math (`mitex inline`). |
| `#mitex(\`...\`)` / `#mitex[...]` | Block math. |

## `touying-mitex` for animations

Touying provides `touying-mitex(mitex, equation)` which lets you put
LaTeX `\pause` markers in the equation:

```typst
#import "@preview/touying:0.7.3": *
#import "@preview/mitex:0.2.6": *
#import themes.simple: *

#show: simple-theme

#touying-mitex(mitex, `
  f(x) &= \pause x^2 + 2x + 1  \\
       &= \pause (x + 1)^2  \\
`)
```

`touying-mitex` is the LaTeX-equation equivalent of the bare-word
`pause` / `meanwhile` inside `$ ... $` — see
[`../tutorial/dynamic/03-equation.md`](../tutorial/dynamic/03-equation.md).

## Example

See [`examples/02-mitex/02-mitex.typ`](./examples/02-mitex/02-mitex.typ).

## Pitfalls

- MiTeX doesn't support every LaTeX package — only the math primitives
  in the LaTeX2e core. `\newcommand`, `\int`, `\sum`, fractions, accents
  all work; `\usepackage{...}` does not.
- `touying-mitex` requires the `mitex` function as its first argument
  (so you can swap implementations).
- For non-animated equations, prefer Typst's native math syntax — it
  compiles faster.
