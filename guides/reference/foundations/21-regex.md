# `regex` — regular expressions

A regex value. Construct with `regex("...")`. The pattern syntax is the [Rust `regex` crate](https://docs.rs/regex/latest/regex/#syntax) (PCRE-ish, no backreferences, no lookaround).

## Where you use it

| Place                            | Example                                             |
| -------------------------------- | --------------------------------------------------- |
| `str.split` separator            | `"a,b;c".split(regex("[,;]"))`                      |
| `str.matches`                    | `"v1.2.3".matches(regex(`\d+`.text))`               |
| `str.find` / `str.position`      | `"abc".find(regex("\w"))`                           |
| `str.replace`                    | `"a 1 b 2".replace(regex("\d"), "?")`               |
| Show-rule selector (set form)    | `#show regex("\d+"): set text(red)`                 |
| Show-rule selector (handler form)| `#show regex("\bTODO\b"): m => box(fill: yellow, m)` |

## Escaping — read this once, save grief later

Both Typst strings and regex patterns use `\` for escapes. Two consequences:

- A regex `\d` is a Typst string `"\d"` — `\d` is **not** a Typst string escape, so the string parser leaves it alone. Both forms work.
- A regex `\\` (literal backslash) is a Typst string `"\\\\"` — string `\\` → regex `\`.
- **Recommended**: use a raw block to dodge the issue entirely:
  ```typst
  regex(`\d+\.\d+\.\d+`.text)
  ```
  No double escaping, no ambiguity. Especially helpful for patterns with `\b`, `\w`, `\d`, etc.

## Show-rule handler signature

When you bind a closure to a regex show rule, the closure receives the matched **content** (a `text` element). Wrap, replace, or annotate it:

```typst
#show regex("\bTODO\b"): m => box(
  fill: rgb("#ffeb3b"),
  inset: (x: 3pt, y: 0pt),
  text(weight: "bold")[#m],
)
```

The `set` form (`#show regex(...): set text(...)`) just restyles the match in place.

## Pitfalls

- **No backreferences, no lookaround.** The Rust regex crate is intentionally restricted for linear-time matching. If you reach for `(?=...)` it will reject.
- **Show rules on a regex run on every render pass.** Heavy regex / heavy handler closures slow compile time linearly with document size.
- **Show rules can compose surprisingly** — when two regex rules' matches overlap, only one fires per character. Order in source determines precedence, latest wins.
- **`regex` is its own type** — you cannot pass a string where a `regex` is expected (e.g. you can't `set page(...)` regex selectors as a string). Always wrap with `regex(...)`.

## Examples (compile-verified)

- `examples/21-regex/01-construct-and-string-methods.typ` — `split`, `matches`, `replace`, raw-block escaping.
- `examples/21-regex/02-show-rule.typ` — both the `set` and handler forms; multi-rule composition with TODO/FIXME highlighting.

## Reference

- Official: https://typst.app/docs/reference/foundations/regex/
- Pattern syntax: https://docs.rs/regex/latest/regex/#syntax
