# `math.primes(count)` — grouped primes

Renders a fixed number of grouped prime marks. You'll usually use the **shorthand syntax** (apostrophes) instead of calling `primes()` directly.

## Parameters

| Param   | Type | Default  | Notes                          |
| ------- | ---- | -------- | ------------------------------ |
| `count` | int   | required | Number of prime marks to draw. |

## Syntax shortcut

| Markup    | Effect                                  |
| --------- | --------------------------------------- |
| `a'`       | One prime: `a′`                         |
| `a''`      | Two primes: `a″`                        |
| `a'''`     | Three primes: `a‴`                      |

Apostrophes auto-attach to the previous token. They occupy a *separate* slot from the regular superscript — so `a'''_b` and `a^'''_b` are equivalent, and a real superscript moves up one level.

## Examples (compile-verified)

- `examples/12-primes/01-primes.typ` — apostrophe shorthand, primes coexisting with subscripts/superscripts, functional notation.

## Reference

https://typst.app/docs/reference/math/primes/
