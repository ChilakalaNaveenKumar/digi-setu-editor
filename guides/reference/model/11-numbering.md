# `numbering` — apply a numbering pattern (or function) to numbers

`numbering(numbering: str | function, ..numbers: int) -> any`

Turns a sequence of non-negative integers into formatted content using either a **pattern string** or a **function**. The same shape is accepted by every other Typst parameter named "numbering" (`heading.numbering`, `figure.numbering`, `enum.numbering`, `math.equation.numbering`, `page.numbering`, `par.line.numbering`, ...).

## Pattern grammar

A pattern is built from three pieces:

| Piece            | Role                                                    | Example                                |
| ---------------- | ------------------------------------------------------- | -------------------------------------- |
| Counting symbols | Each is replaced by the next number in its alphabet      | `1`, `a`, `A`, `i`, `I`, `*`, ...     |
| Prefixes         | Anything between counting symbols, printed as-is         | `.`, `-`, ` -- `                       |
| Suffix           | Anything **after** the last counting symbol, printed once at the end | `)`, `.`, `:`                |

### Counting alphabets

| Symbol(s)             | Sequence                                              |
| --------------------- | ----------------------------------------------------- |
| `1`                   | 1, 2, 3, ...                                          |
| `a`, `A`              | a..z then aa, ab, ... (case preserved)                |
| `i`, `I`              | i, ii, iii, iv, v, ... (case preserved)               |
| `*`                   | * † ‡ § ¶ ‖, then **, ††, ‡‡, ...                     |
| `α` / `Α`             | Greek lowercase / uppercase                            |
| `一` / `壹`           | Chinese (financial / common)                          |
| `あ` / `い` / `ア` / `イ` | Japanese kana sequences                            |
| `א`                   | Hebrew                                                |
| `가` / `ㄱ`           | Korean                                                 |
| `①` / `⓵`             | Circled numbers / dotted circled numbers              |
| `١`, `۱`, `१`, `১`, `ক` | Arabic, Persian, Devanagari, Bengali variants     |

Numbers are 1-based; passing `0` indicates "this position has not yet appeared" (used by counters).

### More numbers than symbols

If you pass more numbers than the pattern has counting symbols, the **last** counting symbol (with its prefix) is **repeated**:

```typst
#numbering("1.", 1, 2, 3, 4)   // -> 1.2.3.4.
#numbering("1.a", 1, 2, 3, 4)  // -> 1.a.b.c
```

## Function form

Pass a function that receives each number as a positional argument and returns content:

```typst
#let unary(..nums) = "|" * nums.pos().last()
#numbering(unary, 3)   // -> |||
```

The pattern parameter accepts function as a value because consumers (heading, figure, enum, ...) need to forward an unknown numbering — calling `numbering(my-numbering, ...)` lets you uniformly handle both shapes.

## Pitfalls

- **Suffix is the trailing part after the LAST counting symbol.** `"1.a"` has no suffix; `"1.a)"` has `)` as suffix. This matters when consumers (e.g. `par.line.numbering: "1"`) emit the result inline.
- **Prefixes attach to the symbol they precede.** `"I-1"` for `(2, 3)` is `II-3`, not `I-2-3`.
- **`*` exhausts after 6.** `numbering("*", 7)` becomes `**` (doubled). To force purely numeric overflow, use `"1"`.
- **Functions don't print prefixes/suffixes for you.** If you switch from `"1."` to a function, you handle dots/parens manually.
- **Pass non-negative ints only.** Negative numbers error.

## Examples (compile-verified)

- `examples/11-numbering/01-patterns-and-functions.typ` — pattern strings, `*` symbol overflow, more numbers than symbols, function form.
- `examples/11-numbering/02-as-heading-numbering.typ` — same pattern + function form supplied to `set heading(numbering:)`.

## Reference

- Official: https://typst.app/docs/reference/model/numbering/
- `counter` (where the integers come from): https://typst.app/docs/reference/introspection/counter/
- Used by: `heading`, `figure`, `enum`, `math.equation`, `page`, `par.line`, `footnote`, `outline`.
