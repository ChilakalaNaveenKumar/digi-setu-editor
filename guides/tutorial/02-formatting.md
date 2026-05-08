# 02 — Formatting

> **Typst version:** 0.14.2
> **Source page:** <https://typst.app/docs/tutorial/formatting/>
> **Audience:** an LLM agent that authors `.typ` files. All examples below are verified to compile clean with `typst 0.14.2` (see `examples/02-formatting/`). Original reference; the canonical Typst tutorial is the human-friendly source.

---

## Mental model — three ways to apply style

| Mechanism | Scope | When to reach for it |
|---|---|---|
| **Wrap inline:** `#fn(args)[content]` | Just the wrapped span | One-off; styling a single span differently |
| **Set rule:** `#set fn(args)` | Everything from this point forward in the enclosing scope | Document-wide defaults |
| **Show rule:** `#show selector: handler` | Every match of the selector | Re-skinning element rendering or substituting strings |

Order of precedence: a more local wrap or a content-block-scoped `set` overrides a document-level `set`. Show rules transform output regardless of how the content was produced.

---

## 1. Inline styling via trailing content block

- **Syntax:** `#fn(named: ..., positional)[ ...markup... ]`. The trailing `[...]` is syntax sugar — it is passed as the **last positional argument** of `fn`. Used by `text`, `align`, `box`, `figure`, `par`, `link`, etc.
- **Example:** [`01-inline-text-wrap.typ`](./examples/02-formatting/01-inline-text-wrap.typ)
- **Pitfalls:**
  - The trailing block must be `[...]`, not `{...}`. Curly braces are a code block, not content.
  - The function must accept a content positional argument; otherwise compile fails.

## 2. Set rule — set defaults for a function

- **Syntax:** `#set fn(arg1: value, arg2: value, ...)`. Conceptually: "set these as the default values for `fn` from here on."
- **Example:** [`02-set-text-font.typ`](./examples/02-formatting/02-set-text-font.typ)
- **Rules:**
  - Only **settable** parameters can be set (the parameters that tell *how*, not *what*). The reference page for each function marks them.
  - Set rules apply **forward in their scope**. A set rule inside `[...]` only affects that content block.
  - Multiple set rules combine (later overrides earlier on a per-arg basis).

## 3. Combine multiple set values in one rule

- **Syntax:** `#set fn(a: ..., b: ..., c: ...)` — same form, comma-separated args.
- **Example:** [`03-set-text-size.typ`](./examples/02-formatting/03-set-text-size.typ)
- **Common length units:** `pt`, `mm`, `cm`, `in`, `em` (font-relative), `%` (container-relative).

## 4. Page paper size

- **Syntax:** `#set page(paper: "<name>")`. Common names: `"a3"`, `"a4"`, `"a5"`, `"a6"`, `"us-letter"`, `"us-legal"`, `"presentation-16-9"`. Or specify `width: ..., height: ...` instead.
- **Example:** [`04-set-page-paper.typ`](./examples/02-formatting/04-set-page-paper.typ)
- **Pitfalls:** Paper name is a string — quoted. Unknown names error at compile time.

## 5. Page margins — symmetric (`x` / `y`)

- **Syntax:** `margin: (x: <len>, y: <len>)` — `x` applies to left+right, `y` to top+bottom.
- **Example:** [`05-set-page-margin-xy.typ`](./examples/02-formatting/05-set-page-margin-xy.typ)
- **Pitfalls:** A bare length (`margin: 1.5cm`) is also valid and applies to all four sides at once.

## 6. Page margins — per side

- **Syntax:** `margin: (left: ..., right: ..., top: ..., bottom: ...)` — any subset; missing keys keep their defaults.
- **Example:** [`06-set-page-margin-named.typ`](./examples/02-formatting/06-set-page-margin-named.typ)
- **Pitfalls:**
  - Don't mix `x`/`y` with per-side keys in the same dictionary.
  - Use this for bound documents where the inside (gutter) margin needs more room.

## 7. Paragraph justification

- **Syntax:** `#set par(justify: true)` enables full justification.
- **Example:** [`07-set-par-justify.typ`](./examples/02-formatting/07-set-par-justify.typ)
- **Pitfalls:** Justification looks bad at narrow column widths. Pair with hyphenation (on by default) for clean results.

## 8. Paragraph leading (line spacing) with `em`

- **Syntax:** `#set par(leading: <length>)`. Use `em` so spacing scales with the current font size: `1em` = current size; `0.65em` = tighter than default.
- **Example:** [`08-set-par-leading-em.typ`](./examples/02-formatting/08-set-par-leading-em.typ)
- **Pitfalls:** Setting `leading` in `pt` couples it to a specific font size. Always prefer `em` so `set text(size: ...)` doesn't break your spacing.

## 9. Heading numbering — decimal (`"1."`)

- **Syntax:** `#set heading(numbering: "1.")`. The pattern is read **character by character**: each counter character (`1`, `a`, `A`, `i`, `I`) selects the format for one heading level; punctuation (`.`, `)`, `-`, ...) is rendered literally between counters.
  - Pattern `"1."` → level-1: `1.`, level-2: `1.1.`, level-3: `1.1.1.`
- **Example:** [`09-set-heading-numbering-decimal.typ`](./examples/02-formatting/09-set-heading-numbering-decimal.typ)
- **Pitfalls:** If you have more nesting levels than counter characters in the pattern, the last counter format repeats.

## 10. Heading numbering — mixed counter formats

- **Counter characters:**
  - `1` arabic digits
  - `a` lowercase letters (`a`, `b`, ..., `aa`)
  - `A` uppercase letters
  - `i` lowercase roman (`i`, `ii`, `iii`)
  - `I` uppercase roman
  - `*` symbols (`*`, `†`, `‡`, `§`, ...)
- **Syntax:** `#set heading(numbering: "1.a")` → level-1 arabic, level-2 lowercase letter.
- **Example:** [`10-set-heading-numbering-letters.typ`](./examples/02-formatting/10-set-heading-numbering-letters.typ)

## 11. Lorem ipsum placeholder

- **Syntax:** `#lorem(<n>)` — emits `n` words of Lorem Ipsum.
- **Example:** [`11-lorem.typ`](./examples/02-formatting/11-lorem.typ)
- **Use case:** layout prototyping before real copy is ready. Remove before shipping.

## 12. Markup is sugar for function calls

- **Equivalences (memorise these):**
  - `= Foo` ≡ `#heading[Foo]` (level inferred from `=` count)
  - `+ item` ≡ `#enum.item[item]` inside an `#enum(...)`
  - `- item` ≡ `#list.item[item]` inside a `#list(...)`
  - `_x_` ≡ `#emph[x]`
  - `*x*` ≡ `#strong[x]`
- **Why this matters:** `#set heading(...)` works on `= Foo` because both go through the same `heading` element internally.
- **Example:** [`12-heading-as-function.typ`](./examples/02-formatting/12-heading-as-function.typ)
- **Pitfalls:** Calling `#heading(level: 2)[Foo]` lets you build a level-2 heading from code (e.g. inside a function), where you can't write `==`.

## 13. Show rule — replace a literal string

- **Syntax:**
  ```
  #show "<literal>": <handler>
  ```
  The handler is a function that receives the matched content as its single argument and returns replacement content. A function-literal handler is `name => <expr>`.
- **Example:** [`13-show-string-replacement.typ`](./examples/02-formatting/13-show-string-replacement.typ)
- **Pitfalls:**
  - String selectors are literal, not regex. Use `regex("...")` selector for patterns.
  - The handler runs every time the literal appears — including inside replacement output. Be careful not to recurse.
  - Wrap multi-piece replacements in `box[...]` to prevent line breaks splitting them.

## 14. 2D alignment with `+`

- **Syntax:** Combine one horizontal (`left | center | right`) with one vertical (`top | horizon | bottom`) using `+`.
- **Example:** [`14-align-2d.typ`](./examples/02-formatting/14-align-2d.typ)
- **Pitfalls:**
  - Vertical alignments inside flowing content typically need a constrained container (a sized page, `block(height: ..., ...)`, or a grid cell) to be visible.
  - You can't combine two horizontals (`left + right`) or two verticals (`top + bottom`).

## 15. Mode rule for nested function calls

- **Inside `(...)` arg list:** code mode → call functions **without** `#`.
- **Inside `[...]` content block:** markup mode → call functions **with** `#`.
- **Inside `$...$`:** math mode → call functions **without** `#`.
- **Example:** [`15-code-mode-inside-brackets.typ`](./examples/02-formatting/15-code-mode-inside-brackets.typ)
- **Pitfall:** When you nest `[...]` inside `(...)` (e.g. `figure(image(...), caption: [#image(...)])`) the inner `[...]` snaps you back to markup, so the inner `image()` needs a `#` again. The mode flips with every bracket type.

---

## Quick reference — set-rule targets used most

| Function | Common settable params |
|---|---|
| `text` | `font`, `size`, `weight`, `style`, `fill`, `tracking`, `lang`, `region` |
| `page` | `paper`, `width`, `height`, `margin`, `header`, `footer`, `numbering`, `columns` |
| `par` | `justify`, `leading`, `first-line-indent`, `linebreaks`, `spacing` |
| `heading` | `numbering`, `outlined`, `bookmarked`, `supplement` |
| `document` | `title`, `author`, `description`, `keywords`, `date` |
| `enum` / `list` | `tight`, `indent`, `marker`/`numbering`, `body-indent` |

## Quick reference — heading numbering counter chars

| Char | Format |
|---|---|
| `1` | Arabic: 1, 2, 3 |
| `a` | Lowercase letter: a, b, c, …, aa, ab |
| `A` | Uppercase letter: A, B, C |
| `i` | Lowercase roman: i, ii, iii |
| `I` | Uppercase roman: I, II, III |
| `*` | Symbols: *, †, ‡, § |

## Quick reference — alignment values

| Horizontal | Vertical |
|---|---|
| `left` | `top` |
| `center` | `horizon` |
| `right` | `bottom` |
| `start` (lang-aware) | |
| `end` (lang-aware) | |

---

## Self-check before shipping any `.typ` file

1. Did each `#set fn(...)` go in the right scope? (Document-wide vs. inside a `[...]` block matters.)
2. For length values, did you use `em` (relative) where layout should follow the font, and `pt`/`cm` (absolute) only where it shouldn't?
3. Heading numbering pattern: does the counter-char count match your deepest heading level?
4. Show rules — are any of your replacements recursive? (The replacement string can re-trigger the same rule.)
5. Mode flips: did you remember `#` after switching back to markup with `[...]`?
6. Does the file actually compile? (`typst compile path.typ /tmp/out.pdf`)
