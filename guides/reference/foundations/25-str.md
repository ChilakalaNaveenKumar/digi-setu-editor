# `str` — Unicode strings

A sequence of Unicode codepoints stored as UTF-8.

## Critical mental model

- **All lengths and indices are BYTE offsets**, not codepoints, not characters, not grapheme clusters.
- Negative indices wrap from the end.
- Slicing or indexing into the middle of a multi-byte codepoint is an error: `"héllo".slice(0, count: 2)` fails because byte 2 is inside `é` (which is `0xC3 0xA9`).
- For "human characters" use `.clusters()` (proper grapheme clusters: emoji + skin tones + combining marks stay together).
- For Unicode codepoints use `.codepoints()`.

## Operators

| Op            | Meaning                                                         |
| ------------- | --------------------------------------------------------------- |
| `s1 + s2`     | concatenation                                                   |
| `s * n`       | repeat `n` times (`n: int`)                                     |
| `pat in s`    | shorthand for `s.contains(pat)` — accepts string OR regex on LHS |
| `s1 == s2`    | byte-wise equality (normalize first if needed — see below)      |
| `for c in s`  | iterates **grapheme clusters**, not codepoints                  |

## Literals

```typst
"plain"
"\\ \" \n \r \t \u{1f600}"  // escapes
```

There is no single-quote string literal. For multiline / no-escape needs, use a **raw block**:

```typst
`multi
line literal`.text   // -> str
```

## Constructor

`str(value, base: int = 10) -> str`

| Input     | Behavior                                                                 |
| --------- | ------------------------------------------------------------------------ |
| `int`     | base 10 by default; pass `base:` (2..36) to override                     |
| `float`   | base 10, **never** scientific (`1e8 → "100000000"`)                      |
| `str`     | identity                                                                 |
| `bytes`   | UTF-8 decode                                                             |
| `label`   | label name, no angle brackets                                            |
| `decimal` | exact decimal text                                                       |
| `version` | dotted form (`"0.14.2"`)                                                 |
| `type`    | type name as a string                                                    |

Negative numbers use the **Unicode minus** `−` (U+2212), not ASCII `-`. Strip and replace if you need ASCII.

## Method reference

### Length / pieces

| Method                      | Returns         | Notes                                              |
| --------------------------- | --------------- | -------------------------------------------------- |
| `.len()`                    | `int`           | UTF-8 byte length                                  |
| `.first(default:)`          | `str`           | first grapheme cluster; errors if empty + no default |
| `.last(default:)`           | `str`           | last grapheme cluster; same                        |
| `.at(index, default:)`      | `str` or `default` | cluster starting at this byte index            |
| `.slice(start, end, count:)`| `str`           | exactly one of `end` or `count` is meaningful      |
| `.clusters()`               | `array<str>`    | grapheme clusters                                  |
| `.codepoints()`             | `array<str>`    | single codepoints                                  |
| `.rev()`                    | `str`           | reversed                                           |

### Unicode

| Method                       | Returns | Notes                                            |
| ---------------------------- | ------- | ------------------------------------------------ |
| `"x".to-unicode()`           | `int`   | codepoint of a SINGLE-character string           |
| `str.from-unicode(n)`        | `str`   | static; n must be a valid codepoint              |
| `.normalize(form:)`          | `str`   | `"nfc"` (default), `"nfd"`, `"nfkc"`, `"nfkd"`   |

When to normalize: equality / search / sort on user-typed input that may mix composed (`é` = U+00E9) and decomposed (`e` + U+0301) forms. NFC for storage / display, NFD for splitting on combining marks. NFKC also folds compatibility forms (`ﬁ → fi`) — use only when that fold is wanted.

### Search / membership

All accept a **pattern** = `str` OR `regex`.

| Method               | Returns          |
| -------------------- | ---------------- |
| `.contains(pat)`     | `bool`           |
| `.starts-with(pat)`  | `bool`           |
| `.ends-with(pat)`    | `bool`           |
| `.find(pat)`         | `str` or `none`  |
| `.position(pat)`     | `int` or `none`  |

Plus the `in` operator: `"abc" in "xabcdy"` and `regex("\d") in "10"`.

### Match introspection

| Method            | Returns                | Notes                                  |
| ----------------- | ---------------------- | -------------------------------------- |
| `.match(pat)`     | `dict` or `none`       | first match; check `== none` first     |
| `.matches(pat)`   | `array<dict>`          | all matches; possibly empty            |

Match dict shape:

```
( start: int, end: int, text: str, captures: array<str> )
```

`captures` is **only** populated for regex patterns with capturing groups, and contains the captures **only** — not the whole match.

### Mutation (returning new string)

| Method                                      | Notes                                                                  |
| ------------------------------------------- | ---------------------------------------------------------------------- |
| `.replace(pat, replacement, count:)`        | `replacement` may be `str` or `function`; function gets the match dict |
| `.trim(pat = none, at:, repeat:)`           | `pat = none` trims whitespace; `at: start | end`; `repeat: false` to trim once |
| `.split(pat = none)`                        | `pat = none` splits on whitespace runs; `pat = ""` separates every codepoint and adds empties at the ends |

## Pitfalls (the ones that bite)

- **Indexing in bytes, not characters.** `"héllo".len() == 6`, not 5. `.at(1)` is fine, `.at(2)` lands in the middle of `é` and errors. Use `.clusters()` if you want to iterate "characters".
- **`"a" + 5` errors.** Strings concatenate only with strings. Coerce numerics with `str(...)` first.
- **Equality is byte-wise.** `"é" == "e\u{0301}"` is `false`. Normalize before comparing if input shape varies.
- **Regex in a markup label is treacherous** — `$` opens math mode, `*` opens bold. Wrap regex display strings in raw blocks (`` `regex(...)` ``) or only show them inside code mode.
- **Match-on-no-match returns `none`.** Don't chain methods on the result without a guard.
- **`str("nope")` doesn't parse — it returns `"nope"`.** For "parse this string as int / float", use `int("...")` / `float("...")`. They error on bad input.
- **Replacement function form** receives a match dict with `text`, `start`, `end`, `captures`. Returning the wrong type is a type error; cast with `str(...)` if you computed something numeric.

## Examples (compile-verified)

- `examples/25-str/01-literals-construct-base.typ` — literals + every escape; `str(...)` from each accepted input type with `base:`.
- `examples/25-str/02-indexing-slicing-clusters.typ` — `len`, `first`, `last`, `at`, `slice` (with the boundary-error caveat), `clusters` vs `codepoints` on emoji-with-modifier, `rev`.
- `examples/25-str/03-unicode-and-normalize.typ` — `to-unicode` / `from-unicode`, NFC vs NFD round-trip, NFKC fold of the `ﬁ` ligature.
- `examples/25-str/04-search-and-membership.typ` — `contains` / `in` (string + regex on LHS), `starts-with` / `ends-with`, `find` / `position` including miss case.
- `examples/25-str/05-match-and-matches.typ` — full match-dict shape with captures, none-handling, `.matches(...).map(...)` for structured extraction.
- `examples/25-str/06-replace-trim-split.typ` — string + function replacement, `count:`, `trim` with `at:` and `repeat:`, split on whitespace / regex / empty string.

## Reference

- Official: https://typst.app/docs/reference/foundations/str/
- Regex pattern syntax: https://docs.rs/regex/latest/regex/#syntax
