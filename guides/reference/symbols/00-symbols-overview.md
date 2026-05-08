# `symbols` — module overview & shorthands

Two modules give names to characters that are hard to type:

| Module    | Where to use                               | Example                  |
| --------- | ------------------------------------------ | ------------------------ |
| `sym`     | General Unicode symbols, math, arrows, etc. | `#sym.arrow.r`, `→` in math: `$ -> $` |
| `emoji`   | Emoji                                       | `#emoji.face.cry`        |

In **math mode** (inside `$...$`), `sym.` symbols are accessible without the prefix: just write `arrow.r`, `pi`, `RR`, `forall`, etc.

You can always also enter the **literal Unicode character** directly into your text. Named access is just an ergonomic alternative when the keyboard doesn't make a glyph easy to type.

In addition to the listed symbols, math mode defines `dif` and `Dif` (used for differentials in integrals like `$ integral f(x) dif x $`) — these affect spacing and font style and are not normal symbol values.

---

## Shorthands (parser-level character sequences)

Shorthands are concise multi-character text patterns the **parser** translates into a glyph. They differ from `sym.` names because they trigger automatically and don't need a function call. Two distinct sets exist depending on the mode.

### Markup-mode shorthands

| Input    | Output    | Description                  |
| -------- | --------- | ---------------------------- |
| `--`      | –         | en dash                      |
| `---`     | —         | em dash                      |
| `...`     | …         | ellipsis                     |
| `-?`      | (invisible) | soft hyphen / hyphenation hint |
| `~`       | (invisible) | non-breaking space           |

To **disable** a shorthand, escape any one character: `\--` becomes literal `--`. Typst's parser only consumes a shorthand when *all* characters are present unescaped.

### Math-mode shorthands

| Input  | Output | Maps to        |
| ------ | ------ | -------------- |
| `->`    | →      | `arrow.r`       |
| `|->`   | ↦      | `arrow.bar`     |
| `=>`    | ⇒      | `arrow.r.double`|
| `|=>`   | ⤇      | `arrow.bar.double` |
| `==>`   | ⟹      | `arrow.r.double.long`|
| `-->`   | ⟶      | `arrow.r.long`  |
| `~~>`   | ⟿      | `arrow.r.squiggly` |
| `~>`    | ⇝      | `arrow.r.squiggly.short` |
| `>->`   | ↣      | `arrow.r.tail`  |
| `->>`   | ↠      | `arrow.r.twohead`|
| `<-`    | ←      | `arrow.l`       |
| `<==`   | ⟸      | `arrow.l.double`|
| `<--`   | ⟵      | `arrow.l.long`  |
| `<~~`   | ⬳      | `arrow.l.squiggly`|
| `<~`    | ⇜      | `arrow.l.squiggly.short`|
| `<-<`   | ↢      | `arrow.l.tail`  |
| `<<-`   | ↞      | `arrow.l.twohead`|
| `<=>`   | ⇔      | `arrow.l.r.double`|
| `<==>`  | ⟺      | `arrow.l.r.double.long` |
| `<-->`  | ⟷      | `arrow.l.r.long`|
| `*`      | ∗      | `ast.op`         |
| `||`     | ‖      | `bar.v.double`   |
| `[|`     | ⟦      | `bracket.l.double`|
| `|]`     | ⟧      | `bracket.r.double`|
| `:=`    | ≔      | `colon.eq`      |
| `::=`   | ⩴      | `colon.double.eq` |
| `=:`    | ≕      | `eq.colon`      |
| `!=`    | ≠      | `eq.not`        |
| `>>`    | ≫      | `gt.double`     |
| `>=`    | ≥      | `gt.eq`         |
| `>>>`   | ⋙      | `gt.triple`     |
| `<<`    | ≪      | `lt.double`     |
| `<=`    | ≤      | `lt.eq`         |
| `<<<`   | ⋘      | `lt.triple`     |
| `-`     | −      | `minus`         |
| `~`     | ∼      | `tilde.op`      |

(See the [official shorthand reference](https://typst.app/docs/reference/symbols/) for the most up-to-date list — Typst occasionally adds more.)

## How to find a symbol

The official `sym` and `emoji` modules contain **thousands** of named glyphs. Two practical lookup strategies:

1. Browse the official lists with in-page search:
   - https://typst.app/docs/reference/symbols/sym/
   - https://typst.app/docs/reference/symbols/emoji/
2. Type the literal Unicode character if you can; both modes accept it.

## Examples (compile-verified)

- `examples/00-overview/01-shorthands.typ` — markup-mode shorthands (en/em dash, ellipsis, nbsp), math-mode shorthands (arrows, relations, fences), escaping.

## Reference

https://typst.app/docs/reference/symbols/
