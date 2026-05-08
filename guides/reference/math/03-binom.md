# `math.binom(upper, ..lower)` — binomial / multinomial coefficient

Renders a vertically stacked `(upper // lower)` enclosed in parentheses.

## Parameters

| Param   | Type     | Default  | Notes                                                            |
| ------- | -------- | -------- | ---------------------------------------------------------------- |
| `upper` | content  | required | Upper index.                                                     |
| `lower` | content (variadic) | required | One or more lower indices — multiple become a multinomial. |

```typst
$ binom(n, k) $                       // standard
$ binom(n, k_1, k_2, ..., k_m) $      // multinomial
```

## Examples (compile-verified)

- `examples/03-binom/01-binom.typ` — standard, multinomial, inside the binomial theorem.

## Reference

https://typst.app/docs/reference/math/binom/
