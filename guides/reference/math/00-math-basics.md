# `math` — module overview and math-mode basics

The `math` module groups all math-typesetting functions. **Math mode** is entered by wrapping content in `$ ... $` — once inside, you write formulas using a special syntax that's distinct from regular markup or code.

## Inline vs block

| Syntax            | Result                                                         |
| ----------------- | -------------------------------------------------------------- |
| `$x^2$`           | **Inline** equation — sits in the text baseline                 |
| `$ x^2 $`         | **Block** equation — own centered line. Triggered by whitespace right after `$` AND right before the closing `$` |

The whitespace rule is strict: `$ x^2$` is inline (no trailing space), `$x^2 $` is inline (no leading space). Only `$ x^2 $` becomes a block.

By default block equations don't break across pages. Allow it with:

```typst
#show math.equation: set block(breakable: true)
```

## Variables, words, and code injection

Inside math mode:

| Token                | Renders as                                       |
| -------------------- | ------------------------------------------------ |
| Single letter `x`    | **Variable** (italic)                            |
| Multi-letter `pi`    | **Identifier / function name** (upright lookup)  |
| `"area"`             | Quoted plain text (upright)                       |
| `#x`                 | Inject code value `x` from the surrounding scope |
| `#x.field`, `#f(...)` | Any code expression via hash                    |

Strings (`"..."`) are usable directly inside math without `#`.

```typst
$ A = pi r^2 $              // 'pi' is a recognized identifier; 'A', 'r' italic
$ "area" = pi dot "radius"^2 $
#let x = 5
$ #x < 17 $                 // injects 5
```

## Symbols & shorthands

Math mode exposes a wide symbol library directly (no `sym.` prefix needed):

| Category    | Examples                                                |
| ----------- | ------------------------------------------------------- |
| Greek       | `alpha`, `beta`, `pi`, `omega`, `Alpha`, `Pi`            |
| Sets        | `RR`, `NN`, `ZZ`, `QQ`, `CC`, `HH`                       |
| Calculus    | `integral`, `partial`, `nabla`, `dif`, `sum`, `product` |
| Logic       | `and`, `or`, `not`, `forall`, `exists`                   |
| Relations   | `<=`, `>=`, `!=`, `in`, `subset`, `tilde`, `equiv`       |
| Modifiers   | `arrow.r`, `arrow.l.r`, `gt.eq.not`, ...                 |

**Shorthands** approximate certain symbols at the parser level: `->`, `<-`, `<->`, `=>`, `<=>`, `|->`, `:=`, `::=`. When a symbol has a shorthand, its docs page lists it.

## Function calls in math (math calls)

Math mode supports function calls **without** the hash prefix:

```typst
$ frac(a^2, 2) $
$ vec(1, 2, delim: "[") $
$ mat(1, 2; 3, 4) $
```

Math calls behave a bit differently:

- Arguments are themselves math (so `vec(a + b)` = math `a + b` in a vector slot).
- To pass a **code value**, use `#`: `mat(..#range(1, 5).chunks(2))`.
- They support positional and named args plus argument spreading.
- They **don't** support trailing content blocks.
- `;` (semicolon) merges preceding comma-separated args into an array — this is how `mat(1, 2; 3, 4)` produces 2 rows.
- To include a literal `,` or `;`, escape it: `\,`, `\;`.
- The `:` is interpreted as a named-argument separator only when directly after an identifier; insert a space before it (` :`) to display it verbatim.

`#fn(...)` (with hash) is a normal code call and follows code rules, not math-call rules.

## Alignment points

`&` creates an alignment column inside a multi-line equation. Successive `&`s **alternate** right-aligned and left-aligned columns:

```typst
$ (3x + y) / 7 &= 9 && "given" \
  3x + y &= 63 & "multiply by 7" $
```

| Slot pattern         | What it does                                        |
| -------------------- | --------------------------------------------------- |
| `expr &= rhs`         | `=` is right-aligned, `rhs` left-aligned             |
| `... && "note"`       | Two `&` in a row open a fresh left-aligned column   |
| `& &` ≡ `&&`          | Same effect                                          |

## Math fonts

Set with a show-set rule. Note: only OpenType **math fonts** (with full math tables) work properly:

```typst
#show math.equation: set text(font: "Fira Math")
$ sum_(i in NN) 1 + i $
```

Default is `New Computer Modern Math` (bundled with Typst).

## Math module access from code

Inside `$...$`, math functions are available bare: `frac`, `mat`, `cancel`, etc. Outside math, prefix with `math.`:

```typst
#math.equation(block: true, $ a^2 + b^2 = c^2 $)
```

## Accessibility (alt text)

For PDF/HTML accessibility, provide `alt:` on `math.equation`:

```typst
#math.equation(
  alt: "d S equals delta q divided by T",
  block: true,
  $ dif S = (delta q) / T $,
)
```

## Pitfalls

- **Single-letter sequences become products.** `$ab$` is `a · b` (italic, multi-letter is the *exception* not the rule). To write a multi-letter identifier, use a known math identifier (`pi`, `sum`) OR quote it (`"area"`) OR define your own with `#let myvar = math.italic[myvar]`.
- **The block trigger is whitespace-sensitive**. `$x^2$` (inline) vs `$ x^2 $` (block) — pay attention to spaces.
- **Math calls vs code calls**. `vec(1, 2)` inside `$...$` is a math call; `#vec(1, 2)` is a code call. Different argument semantics.
- **`,` and `;` are special in math calls** (separators / row-breakers). Escape with `\` to display them.
- **Math mode disables markup formatting** — `*bold*` and `_italic_` aren't recognized. Use `bold(...)`, `italic(...)`, `upright(...)` from the styles module instead.
- **Block equations don't break across pages** by default — set `block(breakable: true)` if you have a long derivation.
- **`#` switches to code, not math**. Inside the resulting code expression, you write code, not math (`#x.method()`, `#range(5)`).

## Examples (compile-verified)

- `examples/00-math-basics/01-math-mode.typ` — inline vs block, variables / words / code injection.
- `examples/00-math-basics/02-symbols-and-shorthand.typ` — Greek letters, set notation, calculus, logic, shorthand operators.
- `examples/00-math-basics/03-alignment-and-linebreaks.typ` — `\` line breaks, `&` alignment columns, `&&` for left-aligned annotations.

## Reference

- Official: https://typst.app/docs/reference/math/
- Symbols list: https://typst.app/docs/reference/symbols/sym/
- `math.equation`: https://typst.app/docs/reference/math/equation/
- LaTeX → Typst guide: https://typst.app/docs/guides/guide-for-latex-users/
