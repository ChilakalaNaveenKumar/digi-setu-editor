// Integration — Theorion theorem environments.
#import "@preview/touying:0.7.3": *
#import themes.university: *
#import "@preview/numbly:0.1.0": numbly
#import "@preview/theorion:0.6.0": *
#import cosmos.clouds: *

#show: show-theorion
#show: university-theme.with(
  aspect-ratio: "16-9",
  config-common(frozen-counters: (theorem-counter,)),
  config-info(title: [Theorion + Touying]),
)
#set heading(numbering: numbly("{1}.", default: "1.1"))

#title-slide()

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

#proof[
  Suppose to the contrary that $p_1, p_2, dots, p_n$ is a finite enumeration
  of all primes. Set $P = p_1 p_2 dots p_n$. Since $P + 1$ is not in our list,
  it cannot be prime. Thus, some prime factor $p_j$ divides $P + 1$, and also
  $P$, hence $1$, a contradiction.
]

#corollary[
  There is no largest prime number.
] <cor_largest_prime>
