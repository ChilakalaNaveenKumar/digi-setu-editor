# 03 — Syntax (Reference)

> **Typst version:** 0.14.2
> **Source page:** <https://typst.app/docs/reference/syntax/>
> **Audience:** an LLM agent that authors `.typ` files. The complete language cheat-sheet — modes, markup, math, code, comments, escapes, identifiers, paths. All examples below are verified to compile clean with `typst 0.14.2` (see `examples/03-syntax/`). Original prose; the canonical Typst reference is the human-friendly source.
>
> **Already covered in earlier guides** (cross-referenced below, not re-shown):
> - Headings (`=`), italic (`_`), bullet/numbered lists (`-`/`+`), labels (`<x>`), references (`@x`), images, figures, bibliography, basic math — see `01-writing-basics.md`.
> - `set` rules, `show` string-targeted rules, content-block syntax sugar, mode-flip-inside-brackets — see `02-formatting.md`.

---

## Modes — the foundation

Typst has **three modes**. The mode you are in determines how characters are interpreted and whether `#` is required to call functions.

| Mode | Default in… | Switch INTO it from elsewhere | Function call |
|---|---|---|---|
| **Markup** | Top of every `.typ` file, content blocks `[ ... ]` | `[ ... ]` (from code) | `#fn(args)` |
| **Math** | Inside `$ ... $` | `$ ... $` (from markup or code) | `fn(args)` (no `#`) |
| **Code** | Inside `( ... )` arg lists, `{ ... }` blocks, after `#` | `#expr` (from markup) | `fn(args)` (no `#`) |

Once in code mode (after `#`), you stay in code until the expression ends — you do not need more hashes for chained calls/operators.

- **Example:** [`01-modes.typ`](./examples/03-syntax/01-modes.typ)
- **Pitfalls:**
  - `#1 + 2` parses as `#1` (code = the integer `1`) followed by literal markup `+ 2`. Use `#(1 + 2)` to keep the whole expression in code.
  - Nesting `(...)` inside `[...]` flips you back to markup → inner function calls need `#` again.

---

## Markup — what's NEW vs. `01-writing-basics.md`

### 1. Strong emphasis and raw

- **Syntax:** `*bold*`. Inline raw: `` `code` ``. Fenced raw with language tag: triple-backticks + lang on the opening fence.
- **Example:** [`02-strong-and-raw.typ`](./examples/03-syntax/02-strong-and-raw.typ)
- **Pitfalls:**
  - `*` adjacent to letters is treated as part of the word, so `**` does NOT make bold-italic by accident — but `*foo* and *bar*` works fine.
  - The fenced language tag (e.g. ` ```python `) controls syntax highlighting only; it doesn't validate the code.

### 2. Forced line break and smart quotes

- **Syntax:** `\` at end of line forces a line break (no paragraph break). Plain `'...'` and `"..."` are auto-converted to typographic quotes (smart quotes, on by default).
- **Example:** [`03-line-and-quote.typ`](./examples/03-syntax/03-line-and-quote.typ)
- **Pitfalls:** The `\` line break has subtly different output from a blank line (`\` keeps the same paragraph; blank line starts a new one).

### 3. ASCII shorthands in markup

| Type | Renders as |
|---|---|
| `~` | non-breaking space |
| `--` | en dash (–) |
| `---` | em dash (—) |
| `...` | horizontal ellipsis (…) |

- **Example:** [`04-symbol-shorthand.typ`](./examples/03-syntax/04-symbol-shorthand.typ)
- **Pitfalls:** `~` in markup is a non-breaking space, NOT a tilde character. Use `\u{007E}` or `#"~"` for a literal tilde.

### 4. Auto-link

- **Syntax:** A bare URL (starting with `http://`, `https://`, etc.) is auto-recognised as a clickable link. For arbitrary anchor text, use `#link(url)[text]`.
- **Example:** [`05-link-auto.typ`](./examples/03-syntax/05-link-auto.typ)

### 5. Term list

- **Syntax:** Each item starts with `/`, then `Term:` (with the colon), then the description.
- **Example:** [`06-term-list.typ`](./examples/03-syntax/06-term-list.typ)
- **Pitfalls:** The colon is required. Without it, `/` at line start has no special meaning.

### 6. Code expression embeds

- **Three forms:**
  - `#identifier` — variable access
  - `#fn(args)` or `#fn[content]` — function call
  - `#(expression)` — any expression (REQUIRED for binary operators)
- **Example:** [`07-code-expression-embeds.typ`](./examples/03-syntax/07-code-expression-embeds.typ)
- **Pitfall (recurring):** `#1 + 2` ≠ `#(1 + 2)`. Always parenthesise compound expressions.

---

## Comments and escapes

### 7. Comments

- **Syntax:** `// line comment` and `/* block comment */`. Comments are stripped, produce no output. Both forms work in markup, math, and code.
- **Example:** [`09-comments.typ`](./examples/03-syntax/09-comments.typ)

### 8. Character escapes

- **Backslash escape:** prefix any "special" character with `\` to render it literally. Common: `\#`, `\$`, `\<`, `\@`, `\*`, `\_`, `\[`, `\]`, `\\`.
- **Unicode escape:** `\u{HEX}` inserts the codepoint with that hex value. Same syntax works inside string literals.
- **Example:** [`08-character-escapes.typ`](./examples/03-syntax/08-character-escapes.typ)

---

## Math — what's NEW vs. `01-writing-basics.md`

### 9. Alignment point + line break

- **Syntax:** `&` marks an alignment column inside math; `\` is a math-mode line break. Together they typeset multi-line aligned equations.
- **Example:** [`10-math-alignment-point.typ`](./examples/03-syntax/10-math-alignment-point.typ)
- **Pitfalls:** Multiple `&` per line define multiple alignment columns (alternating align/space). One `&` per line is the common case.

### 10. ASCII shorthands and code embedding in math

- **ASCII shorthands** (rendered as their math symbols):

| ASCII | Symbol |
|---|---|
| `->` | → |
| `=>` | ⇒ |
| `<-` | ← |
| `<=>` | ⇔ |
| `!=` | ≠ |
| `<=` | ≤ |
| `>=` | ≥ |

- **Code embedding:** `#fn(args)` or `#identifier` inside `$...$` evaluates the expression in code mode and inserts the result.
- **Field access on a symbol:** `arrow.r.long` selects the variant.
- **Example:** [`11-math-code-and-shorthand.typ`](./examples/03-syntax/11-math-code-and-shorthand.typ)

---

## Identifiers

### 11. Naming rules and conventions

- **Allowed characters:** letters (any Unicode letter), digits, `-`, `_`. Must start with a letter or `_`.
- **Convention:** kebab-case (`build-number`, `is-green`).
- **Hyphen ambiguity:** Inside an identifier, `-` is part of the name. As an operator it requires whitespace: `a - b` (subtraction) vs `a-b` (single identifier).
- **Example:** [`12-identifiers.typ`](./examples/03-syntax/12-identifiers.typ)
- **Pitfalls:**
  - `-foo` is the unary negation of `foo`, NOT an identifier starting with `-`.
  - Identifiers cannot start with a digit.

---

## Code-mode literals

### 12. Primitive literals

| Form | Meaning |
|---|---|
| `none` | absence of a value (function default sentinel) |
| `auto` | smart-default sentinel (different from `none`) |
| `true`, `false` | booleans |
| `42` | decimal integer |
| `0xFF` | hex integer |
| `0o77` | octal integer |
| `0b1011` | binary integer |
| `3.14`, `1e5`, `2.5e-3` | floats |

- **Example:** [`13-literals-numbers.typ`](./examples/03-syntax/13-literals-numbers.typ)
- **Pitfalls:** `none == false` is **false**. They are different types — use `none` for "absent", `false` for "this boolean is no".

### 13. Dimension and ratio literals

| Form | Type | Use |
|---|---|---|
| `12pt`, `3mm`, `1cm`, `0.7in` | length (absolute) | font size, margins, fixed sizes |
| `1.2em` | length (font-relative) | line spacing, font-relative spacing |
| `90deg`, `1rad` | angle | `rotate`, gradients |
| `2fr` | fraction | grid columns, flexible space |
| `75%` | ratio | percentages of a parent dimension |

- **Example:** [`14-literals-dimensions.typ`](./examples/03-syntax/14-literals-dimensions.typ)
- **Pitfalls:** Mixing absolute and font-relative lengths can break layouts when the font size changes. Prefer `em` for spacing that should follow the font.

### 14. Strings

- **Syntax:** Always **double-quoted**. Escapes inside: `\"`, `\\`, `\n`, `\r`, `\t`, `\u{HEX}`.
- **Example:** [`15-strings-and-escapes.typ`](./examples/03-syntax/15-strings-and-escapes.typ)
- **Pitfalls:**
  - Single-quoted `'foo'` is **not** a string in code mode — in markup it becomes a smart-quoted text fragment.
  - To embed a literal `\n` (the two characters) inside a string, write `\\n`.

---

## Containers

### 15. Arrays and the single-element gotcha

- **Syntax:** `(a, b, c)`. Empty: `()`. **Single element MUST have a trailing comma**: `(x,)` is a 1-element array; `(x)` is just `x` in parentheses.
- **Example:** [`16-arrays-and-tuple.typ`](./examples/03-syntax/16-arrays-and-tuple.typ)
- **Pitfalls (frequent agent bug):**
  - `(42)` is the integer `42`, not an array.
  - `(42,)` is the array `(42,)`.

### 16. Dictionaries

- **Syntax:** `(key: value, key: value, ...)`. Empty dictionary literal: `(:)` (NOT `()`, which is the empty array).
- **Access:** dot for static keys (`d.k`); `.at("k")` for dynamic keys; `.keys()`, `.values()`, `.pairs()` for iteration.
- **Example:** [`17-dictionaries.typ`](./examples/03-syntax/17-dictionaries.typ)
- **Pitfalls:**
  - Keys are identifiers in the literal (no quotes), but become string keys at runtime.
  - `()` (empty parens) is empty array. `(:)` (with colon) is empty dict. Mixing them up is the second-most-frequent agent bug after the single-element-array trap.

---

## Blocks

### 17. Code block vs content block

| Block | Syntax | What it holds | Result type |
|---|---|---|---|
| **Code** | `{ stmt; stmt; expr }` | Multiple expressions (separated by `;` or newline). `let` bindings yield `none`. | The **joined** value of all sub-expressions. |
| **Content** | `[ ...markup... ]` | Arbitrary markup. | A `content` value. |

- **Example:** [`18-blocks.typ`](./examples/03-syntax/18-blocks.typ)
- **Joining rule:** values in a code block are joined left-to-right. `none + x == x`. Strings concatenate. Content concatenates. Numbers add.

---

## Bindings and destructuring

### 18. `let` bindings

- **Forms:**
  - `let name = expr` — variable binding.
  - `let name(params) = expr` — named function (sugar for `let name = (params) => expr`).
  - `let name` (no `= ...`) — initialises to `none`.
- **Example:** [`19-let-bindings.typ`](./examples/03-syntax/19-let-bindings.typ)
- **Pitfalls:** `let` does not return a value — it yields `none`. So `let x = 1` mid-expression contributes nothing to the join.

### 19. Destructuring patterns

- **Where:** LHS of `let`, function parameters, for-loop binding, plain assignment.
- **Patterns:**
  - Array: `let (a, b, c) = (1, 2, 3)`
  - Discard: `let (_, y, _) = (1, 2, 3)`
  - Rest: `let (first, ..rest) = (1, 2, 3, 4)` → `first=1`, `rest=(2,3,4)`
  - Dict (same name): `let (p50, p99) = (p50: 12, p99: 98)`
  - Dict (rename): `let (p99: tail) = (p99: 98)` → `tail=98`
- **Example:** [`20-destructuring.typ`](./examples/03-syntax/20-destructuring.typ)

---

## Operators

### 20. Operator table (high precedence first)

| Op | Effect | Arity |
|---|---|---|
| `-`, `+` | Negation, no-op | unary |
| `*`, `/` | Multiply, divide | binary |
| `+`, `-` | Add, subtract; `+` also concatenates strings/arrays/content/dicts | binary |
| `==`, `!=`, `<`, `<=`, `>`, `>=`, `in`, `not in` | Comparison and membership | binary |
| `not` | Logical not | unary |
| `and` | Short-circuit AND | binary |
| `or` | Short-circuit OR | binary |
| `=`, `+=`, `-=`, `*=`, `/=` | Assignment / compound assignment | binary |

- **Example:** [`21-operators.typ`](./examples/03-syntax/21-operators.typ)
- **Pitfalls:**
  - `+` is overloaded: numbers add, strings/arrays/content/dicts concatenate. Mixing types errors.
  - `in` checks substring on strings, membership on arrays, key-existence on dicts.

---

## Control flow

### 21. `if`, `for`, `while`, `break`, `continue`

- **All are expressions** — they yield a (joined) value, so you can `let x = if ... { a } else { b }`.
- **Body** can be a code block `{...}` or a content block `[...]`.
- **For-loop iterables:** array (item), string (grapheme cluster), dict (`(key, value)` pair, destructurable), bytes (each `u8`).
- **Example:** [`22-control-flow.typ`](./examples/03-syntax/22-control-flow.typ)
- **Pitfalls:**
  - Iterating a string yields **graphemes**, not codepoints (a flag emoji is one item, not two).
  - `for ... in dict` is more efficient than `for ... in dict.pairs()` — no temporary array.

---

## Functions, closures, methods, fields

### 22. Closures

- **Syntax:** `(params) => body`. Single-param arg-less form: `name => body`. Body can be a code block.
- **Example:** [`23-closures.typ`](./examples/03-syntax/23-closures.typ)
- **Equivalence:** `let f(x) = expr` ≡ `let f = x => expr`.

### 23. Field access and method calls

- **Field:** `value.field` — works on dictionaries (key), modules (definition), symbols (variant), content (element field).
- **Method:** `value.method(args)` is sugar for `type(value).method(value, args)`.
- **Example:** [`24-method-and-fields.typ`](./examples/03-syntax/24-method-and-fields.typ)
- **Mutating methods (e.g. `array.push`)** must be called via method form. To discard the return value of a mutating method, bind to `_`: `let _ = arr.remove(0)`.

---

## Modules and packages

### 24. Imports and includes

| Form | Effect |
|---|---|
| `#import "f.typ"` | Evaluate `f.typ`, bind the resulting module to `f` (filename stem) in current scope. |
| `#import "f.typ": a, b` | Bring named items `a` and `b` into current scope. |
| `#import "f.typ": *` | Bring **everything** into scope (use sparingly). |
| `#import "f.typ" as alias` | Rename the imported module binding. |
| `#import "f.typ": a as one, b as two` | Rename individual items. |
| `#include "f.typ"` | Evaluate `f.typ` and **insert its content** at the call site (no name binding). |

- **Example:** [`25-modules.typ`](./examples/03-syntax/25-modules.typ) (with `_helpers.typ`)

### 25. Packages (preview namespace)

- **Syntax:** `#import "@preview/<name>:<version>": items` — pulls from the community registry.
- **First-time use** downloads the package; offline builds need it pre-cached.
- **No example file** for this page (would require network + a specific version pin).

---

## Paths

### 26. Relative vs absolute, project root

- **Relative path** (no leading `/`): resolved from the directory of the current `.typ` file.
- **Absolute path** (leading `/`): resolved from the **project root**.
- **Project root** defaults to the directory of the main file. Override with the CLI `--root <dir>` flag (the main file must still be inside that root).
- **Security:** files outside the project root cannot be read.
- **Packages:** inside a package, an absolute path resolves to the **package** root, not the project root. A package cannot directly read project files — pass them in as arguments (e.g. an already-loaded `image(...)` value).
- **Example:** [`26-paths.typ`](./examples/03-syntax/26-paths.typ)

---

## Quick reference — symbol cheat-sheet (everything in one place)

### Markup line-starts (column 1, after optional leading whitespace)

| Token | Element |
|---|---|
| `=`, `==`, ... | Heading (level by `=` count) |
| `+ ` | Numbered list item |
| `- ` | Bullet list item |
| `/ Term: …` | Term-list item |

### Inline markup

| Token | Effect |
|---|---|
| `*x*` | Strong |
| `_x_` | Italic |
| `` `x` `` | Inline raw |
| ` ```lang\n…\n``` ` | Fenced raw block |
| `\` (end of line) | Forced line break |
| `~`, `--`, `---`, `...` | nbsp, en dash, em dash, ellipsis |
| `'x'`, `"x"` | Smart quotes |
| `<label>` | Label (after the element to label) |
| `@key` | Reference / cite |
| `#expr` | Code expression embed |
| `\X` | Character escape |
| `\u{HEX}` | Unicode escape |

### Math (delta from page 1)

| Token | Effect |
|---|---|
| `&` | Alignment column |
| `\` (in `$…$`) | Math line break |
| `->`, `=>`, `<-`, `<=>`, `!=`, `<=`, `>=` | ASCII → Unicode math symbol |
| `name.variant` | Symbol variant |
| `#expr` (in `$…$`) | Code embed |

### Code mode

| Token | Meaning |
|---|---|
| `none`, `auto`, `true`, `false` | Singleton literals |
| `42`, `0xFF`, `0o77`, `0b1011` | Integers (decimal, hex, octal, binary) |
| `3.14`, `1e5` | Floats |
| `1cm`, `1.2em`, `90deg`, `2fr`, `75%` | Dimension/angle/fraction/ratio |
| `"x"` | String |
| `(a, b, c)`, `(x,)`, `()` | Array (note 1-tuple comma) |
| `(k: v, ...)`, `(:)` | Dict (note empty-dict colon) |
| `{ … }` | Code block |
| `[ … ]` | Content block |
| `(expr)` | Parenthesised expression |
| `..args` | Argument spread |
| `(x) => expr` | Closure |
| `let`, `set`, `show`, `if`, `else`, `for`, `while`, `break`, `continue`, `return`, `import`, `include`, `as`, `in`, `not`, `and`, `or`, `context` | Reserved keywords |

---

## Self-check before shipping any `.typ` file

1. Is every `#` correctly placed? (`#fn(args)` in markup; no `#` inside `(...)` arg lists or `$...$`; `#` again inside nested `[...]`.)
2. Did you parenthesise every binary operator embed? (`#(a + b)`, not `#a + b`.)
3. Single-element arrays: did you remember the trailing comma? (`(x,)`)
4. Empty dictionary: `(:)` not `()`.
5. Multi-character math sub/superscripts wrapped in `(...)`?
6. Imports — did you list all needed names after the colon?
7. Identifiers — kebab-case, start with letter or `_`, no leading digit?
8. Does it compile? (`typst compile path.typ /tmp/out.pdf`)
