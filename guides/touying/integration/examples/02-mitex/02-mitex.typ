// Integration — MiTeX (LaTeX equations in Typst).
#import "@preview/touying:0.7.3": *
#import "@preview/mitex:0.2.6": *
#import themes.simple: *

#show: simple-theme.with(aspect-ratio: "16-9")

== Inline + block LaTeX
Write inline equations like #mi("x") or #mi[y].

Block equations:
#mitex(`
  \newcommand{\f}[2]{#1f(#2)}
  \f\relax{x} = \int_{-\infty}^\infty
    \f\hat\xi\,e^{2 \pi i \xi x}
    \,d\xi
`)

== `touying-mitex` for animated LaTeX
#touying-mitex(mitex, `
  f(x) &= \pause x^2 + 2x + 1  \\
       &= \pause (x + 1)^2  \\
`)
