# `sym` — named general symbols

Module of named Unicode symbols. Use `#sym.<name>` in markup; in **math mode** drop the prefix.

| Mode    | Access                          |
| ------- | ------------------------------- |
| Markup  | `#sym.arrow.r` → `→`            |
| Math    | inside `$...$`, just `arrow.r`  |

You can always also enter the literal Unicode character directly. Named access is for ergonomics.

## Modifier syntax (dot notation)

Symbols use chained dots to reach variants. Examples for arrows:

| Name                | Glyph |
| ------------------- | ----- |
| `arrow.r`            | →     |
| `arrow.l`            | ←     |
| `arrow.l.r`          | ↔     |
| `arrow.r.double`     | ⇒     |
| `arrow.r.long`       | ⟶     |
| `arrow.r.squiggly`   | ⟿     |
| `arrow.r.tail`       | ↣     |
| `arrow.r.twohead`    | ↠     |
| `arrow.r.bar`        | ↦     |
| `arrow.t`            | ↑     |
| `arrow.b`            | ↓     |

## Modifier vocabulary

These dot-tokens recur across many symbol families:

| Modifier        | Meaning                            |
| --------------- | ---------------------------------- |
| `.l` / `.r`     | left / right                       |
| `.t` / `.b`     | top / bottom                       |
| `.double`       | doubled glyph                      |
| `.triple`       | tripled                            |
| `.long`         | longer variant                     |
| `.short`        | shorter variant                    |
| `.small`        | smaller / tighter                  |
| `.alt`          | alternative form                   |
| `.inv`          | inverse / reversed                 |
| `.filled` / `.stroked` | filled vs outlined          |
| `.heavy` / `.bold` | weight variants                  |
| `.not`          | negated form                       |
| `.bar`          | with a bar                         |
| `.dot`          | with a dot                         |
| `.eq`           | "or equal"                         |
| `.tilde`        | with a tilde                       |
| `.curly` / `.dot` | shape variants for delimiters    |

## Common families

| Family       | Examples                                                            |
| ------------ | ------------------------------------------------------------------- |
| Greek lower  | `alpha`, `beta`, ..., `omega`                                       |
| Greek upper  | `Alpha`, `Beta`, ..., `Omega` (also `Theta.alt`, `Omega.inv`)       |
| Number sets  | `NN`, `ZZ`, `QQ`, `RR`, `CC`, `HH` (blackboard bold)                |
| Hebrew       | `aleph`, `beth`                                                     |
| Operators    | `dot`, `dot.c`, `times`, `div`, `plus.minus`, `minus.plus`           |
| Relations    | `eq.not`, `lt.eq`, `gt.eq`, `tilde.eq`, `equiv`, `prec`, `succ`     |
| Logic        | `forall`, `exists`, `and`, `or`, `not`, `top`, `bot`                |
| Sets         | `in`, `subset`, `subset.eq`, `union`, `sect` (intersection)         |
| Calculus     | `integral`, `partial`, `nabla`, `infinity` (or `oo`), `sum`, `product` |
| Brackets     | `bracket.l`, `bracket.r`, `bracket.l.double`, `angle.l`, `angle.r`  |
| Dots         | `dots.h`, `dots.v`, `dots.up`, `dots.down`, `dots.c`                |
| Geometry     | `circle`, `square`, `triangle.r`, `star`                            |

## Special math-mode entries: `dif`, `Dif`

These are not normal symbols — they affect spacing and font style automatically. Used in integrals to render the differential `d`:

```typst
$ integral_0^1 f(x) dif x $        // proper spacing & upright 'd'
$ integral.double f(x, y) dif x dif y $
```

Outside math, access them as `math.dif` and `math.Dif`.

## Defining your own named symbols

Use the [`symbol(...)` constructor](../foundations/26-symbol.md):

```typst
#let star-strict = symbol("\u{2606}")  // outline star, no modifiers
```

For custom symbols *with* modifiers, pass tuples to `symbol()`:

```typst
#let arr = symbol(
  ("r", "→"),
  ("l", "←"),
  ("up", "↑"),
)
#arr.r #arr.l #arr.up
```

## Examples (compile-verified)

- `examples/01-sym/01-sym-modifiers.typ` — arrows, blackboard-bold sets, Greek letters, operators, brackets, dots, math-mode usage without prefix.

## Reference

https://typst.app/docs/reference/symbols/sym/
