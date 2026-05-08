# Integration — Theorion

> Source: <https://touying-typ.github.io/docs/integration/theorion>
>
> Package: [`theorion`](https://github.com/OrangeX4/typst-theorion) v0.6.0

[Theorion](https://github.com/OrangeX4/typst-theorion) provides
beautifully-typeset theorem environments — `definition`, `theorem`,
`example`, `corollary`, `proof`, etc. It works out-of-the-box with
Touying as long as you **freeze the theorem counter**.

## Setup

```typst
#import "@preview/touying:0.7.3": *
#import themes.university: *
#import "@preview/numbly:0.1.0": numbly
#import "@preview/theorion:0.6.0": *
#import cosmos.clouds: *

#show: show-theorion
#show: university-theme.with(
  aspect-ratio: "16-9",
  config-common(frozen-counters: (theorem-counter,)),
)
#set heading(numbering: numbly("{1}.", default: "1.1"))

= Theorems
== Prime numbers

#definition[
  A natural number is called a #highlight[_prime number_] if it is greater
  than 1 and cannot be written as the product of two smaller natural numbers.
]

#example[
  The numbers $2$, $3$, and $17$ are prime.
  @cor_largest_prime shows that this list is not exhaustive!
]

#pause

#theorem(title: "Euclid")[
  There are infinitely many primes.
]

#pagebreak(weak: true)

#proof[
  Suppose to the contrary that $p_1, p_2, dots, p_n$ is a finite enumeration
  of all primes. Set $P = p_1 p_2 dots p_n$. Since $P + 1$ is not in our list,
  it cannot be prime. Thus, some prime factor $p_j$ divides $P + 1$. Since
  $p_j$ also divides $P$, it must divide the difference $(P + 1) - P = 1$, a
  contradiction.
]

#corollary[
  There is no largest prime number.
] <cor_largest_prime>

#corollary[
  There are infinitely many composite numbers.
]
```

## Why `frozen-counters` is required

Touying renders each subslide by re-evaluating slide content. Without
`frozen-counters`, Theorion's internal `theorem-counter` would
**increment on every subslide**, causing theorem numbers to jump
unexpectedly during `#pause` reveals.

`config-common(frozen-counters: (theorem-counter,))` tells Touying to
capture the counter at the start of each slide and restore it before
rendering each subslide.

## Multiple counter types

If you also have figure counters that should be frozen:

```typst
config-common(frozen-counters: (
  theorem-counter,
  figure.where(kind: image),
))
```

You can list any number of counters (passed as a tuple).

## Cosmos styles

Theorion ships with several visual styles:

- `cosmos.clouds`
- `cosmos.fancy`
- `cosmos.aurora`
- *(more — see the [Theorion repo](https://github.com/OrangeX4/typst-theorion))*

Pick one with `#import cosmos.<name>: *`.

## Example

See [`examples/06-theorion/06-theorion.typ`](./examples/06-theorion/06-theorion.typ).

## Pitfalls

- `theorem-counter` is **a single value**, but `frozen-counters` expects
  a **tuple**. Wrap it: `(theorem-counter,)` (note the trailing comma).
- `#show: show-theorion` is mandatory — it installs theorem-environment
  show rules.
- Theorion uses `pagebreak(weak: true)` between long proofs; this
  interacts cleanly with Touying's slide layout (the proof continues on
  the next slide with the heading "[Section] (cont.)" by default).
- For best results, set heading numbering with `numbly` so theorem
  references like `@cor_largest_prime` render with the right format.
