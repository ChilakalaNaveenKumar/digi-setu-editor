# `raw` — verbatim / monospace text with optional syntax highlighting

`raw(text: str, block: bool = false, lang: none | str = none, align: alignment = start, syntaxes: str | bytes | array = (), theme: none | auto | str | bytes = auto, tab-size: int = 2) -> content`

Renders text **verbatim** in a monospace font. The standard way to embed code in a document.

## Markup shorthand

| Markup                       | Result                                         |
| ---------------------------- | ---------------------------------------------- |
| `` `inline` ``               | Inline raw, no language tag                    |
| ``` ` ` ```                  | Empty raw text                                 |
| ``` ``` ... ``` ```          | Block raw, no highlighting                      |
| ``` ```rust ... ``` ```      | Block raw with `rust` syntax highlighting       |

To include backticks **in** the raw text, use 4+ backticks on the outside; the closing fence must use the same count. Leading/trailing single spaces are trimmed (so you can have `` `inside backticks` `` come out clean).

If three or more backticks are used and the content has at least one line break, `block` is automatically `true` (block raw).

## Inside raw, nothing is interpreted

No escapes, no `*bold*`, no math, no comments. The ONE exception is the language tag immediately after the opening backticks (when there are 3+ of them).

If your content **starts** with something that looks like an identifier but you don't want it parsed as a `lang`, prefix with a single space (which gets trimmed):

````
``` not-a-lang content here
```
````

## Parameters

| Field        | Default       | Notes                                                                       |
| ------------ | ------------- | --------------------------------------------------------------------------- |
| `text`       | (required)    | The verbatim string                                                          |
| `block`      | `false`       | `true` = block raw (own paragraph); `false` = inline                         |
| `lang`       | `none`        | Language tag for highlighting. Includes `"typ"`/`"typc"`/`"typm"` for Typst itself |
| `align`      | `start`       | Per-line alignment within the block                                          |
| `syntaxes`   | `()`          | Path(s) / bytes for additional Sublime-style syntax definitions             |
| `theme`      | `auto`        | `auto` = Typst default theme. `none` disables highlighting. Or path / bytes |
| `tab-size`   | `2`           | Spaces per tab                                                                |

## Default styling

- Font: `DejaVu Sans Mono` (bundled)
- Size: `0.8em` (80% of normal — monospace fonts look bigger)
- Inside raw: hyphenation, overhang, CJK-Latin spacing, and (for blocks) justification are **disabled** by default.

Override globally:

```typst
#show raw: set text(font: "Cascadia Code")
#show raw.where(block: true): set text(1em / 0.8)  // reset block size
```

## `raw.line` — per-line custom rendering

Each line in a raw block is wrapped in a `raw.line` element with these fields:

| Field        | What                                          |
| ------------ | --------------------------------------------- |
| `it.number`  | Line number (1-based)                         |
| `it.count`   | Total number of lines in the block             |
| `it.text`    | Raw text of this line (no highlighting)       |
| `it.body`    | Highlighted content for this line              |

This is how you add line numbers, alternating backgrounds, or any custom per-line layout.

## Custom themes

`theme:` accepts a path to a `.tmTheme` file (Sublime Text format). The theme only affects the **highlight colors**; foreground / background remain under your control. To get a full dark-mode look:

```typst
#set raw(theme: "halcyon.tmTheme")
#show raw: it => block(
  fill: rgb("#1d2433"),
  inset: 8pt,
  radius: 5pt,
  text(fill: rgb("#a2aabc"), it),
)
```

## Custom syntaxes

Drop in a Sublime `.sublime-syntax` file via `syntaxes:` to highlight a language Typst doesn't ship with. You can also abuse this for DSLs — define a fake language and write a show rule that interprets the content:

```typst
#show raw.where(lang: "mydsl"): it => {
  let sum = 0
  for part in it.text.split("+") { sum += int(part.trim()) }
  sum
}

```mydsl
1 + 2 + 3
```
```

## Pitfalls

- **`set` rules don't work directly on raw blocks** the same way as on plain text. Use `show raw: set text(...)` or `show raw: it => ...`.
- **Backtick imbalance is a hard error**, not silent. The opening and closing fences must have the same count of backticks.
- **Language tag follows the OPENING backticks immediately** with no space. ``` ```rust ``` is highlighted; ``` ``` rust ``` treats `rust` as content.
- **`raw` does not auto-wrap long lines.** A long line overflows the page width unless your show rule wraps it. Common fix: `#show raw: it => block(width: 100%, breakable: true, it)` plus letting the monospace font handle wrap.
- **Highlight colors come from the active theme.** If you change the page background, also adjust `theme` foreground-color expectations or set explicit `text(fill:)` in a show rule.
- **`tab-size: 2`** is the default — many code styles want 4. Set it explicitly for files that use tabs.

## Examples (compile-verified)

- `examples/06-raw/01-raw-syntax.typ` — inline vs block, `lang:` highlighting (rust/python), backtick escaping, programmatic `#raw(...)`.
- `examples/06-raw/02-styling-show-rules.typ` — font swap, size-resetting block raw to 1em, inline-raw box, block-raw padded fill, `typ`/`typc`/`typm` self-highlighting.
- `examples/06-raw/03-line-numbers.typ` — `raw.line` show rule adding right-aligned gray line numbers via `grid`.

## Reference

- Official: https://typst.app/docs/reference/text/raw/
- `text` (font selection): https://typst.app/docs/reference/text/text/
- Sublime syntax format: https://www.sublimetext.com/docs/syntax.html
- tmTheme format: https://www.sublimetext.com/docs/color_schemes_tmtheme.html
