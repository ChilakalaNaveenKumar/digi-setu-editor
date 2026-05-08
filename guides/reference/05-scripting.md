# Scripting – Code Mode and Control Flow

Markup and code share a single Typst document. This page documents
the *code* side: expressions, blocks, bindings, control flow, fields,
methods, modules, packages, and operators.

## Markup ↔ code

Typst defaults to **markup mode**. Switch to a single code expression
with `#`:

```typst
#emph[Hello]                // function call
#emoji.face                 // field access on a module
#"hello".len()              // method on a string
```

A trailing semicolon (`#expr;`) ends the expression early. Escape a
literal `#` or `;` with a backslash.

Some expressions can't follow `#` directly (e.g. binary arithmetic).
Wrap them in parens: `#(1 + 2)`.

## Blocks

Two kinds. They can be nested arbitrarily.

| Block          | Syntax       | Returns                 | Use for                                  |
| -------------- | ------------ | ----------------------- | ---------------------------------------- |
| Code block     | `{ ... }`    | Joined value of inner expressions | Multi-statement code, intermediate variables. |
| Content block  | `[ ... ]`    | A `content` value       | Markup as a value: pass it around, store it. |

```typst
#{
  let a = [from]
  let b = [*world*]
  [hello ]
  a + [ the ] + b
}
// → "hello from the world"
```

The two main rules to remember:

- A code block joins all its non-`none` outputs into one value
  (numbers add, content concatenates, arrays concatenate, etc.).
- A content block is a *value* of type `content` — it is **not**
  evaluated in place; it can be stored, passed, returned.

## Bindings

`let` introduces a variable. Without an initializer the value is
`none`. Variable names can include `-` but can't start with one.

```typst
#let name = "Typst"
#let inc(x) = x + 1            // function definition
#name's docs.
#inc(4) is #inc(4).
```

A variable is visible from its `let` to the end of its containing
block (or end of file at the top level).

### Destructuring

`let` can pattern-match arrays and dictionaries. Use `..` once to
collect "the rest"; use `_` to discard.

```typst
#let (x, y) = (1, 2)                  // (x, y) = positional
#let (a, .., b) = (1, 2, 3, 4)        // a=1, b=4
#let (Austen,) = (Austen: "Persuasion", Homer: "Odyssey")   // pick by key
#let (Homer: h) = (Homer: "Odyssey")  // pick + rename
#let (Homer, ..rest) = books          // pick one + collect remainder
#let (_, mid, _) = (1, 2, 3)          // ignore first and last
```

Destructuring also works in **function parameter lists** and on the
left-hand side of plain assignments (handy for swapping):

```typst
#let zip-add = ((a, b)) => a + b      // destructure one tuple arg
#((1, 2), (3, 4)).map(zip-add)        // (3, 7)

#{
  let a = 1; let b = 2
  (a, b) = (b, a)                     // swap
  [a=#a, b=#b]
}
```

## Conditionals

```typst
#if x > 0 [positive] else if x < 0 [negative] else [zero]
```

The body of each branch can be a **code block** or a **content
block**. The conditional yields the chosen branch's value (so an
`if` can be used as an expression).

## Loops

```typst
#for c in "ABC" [#c is a letter. ]      // iterates grapheme clusters
#for v in (1, 2, 3) [...]
#for (k, v) in dict [...]               // direct destructuring
#for byte in bytes("😀") [#byte ]       // iterate bytes
#while n < 10 { n = (n * 2) - 1 }
```

The loop body can be a code or content block. Iteration values are
joined into one (just like blocks).

| Iterator             | What it yields                                        |
| -------------------- | ----------------------------------------------------- |
| `for x in array`     | each element                                          |
| `for (k, v) in dict` | each key-value pair (more efficient than `.pairs()`)  |
| `for c in string`    | each grapheme cluster (a flag emoji counts as one)    |
| `for b in bytes`     | each byte as `int 0..255`                             |

`break` and `continue` work as expected:

```typst
#for letter in "abc nope" {
  if letter == " " { break }
  letter
}
// → "abc"
```

## Fields

Dot notation works on:

- **Dictionaries** — `dict.key`.
- **Symbols** — `sym.arrow.r` selects the modifier.
- **Modules** — `calc.max`, `emoji.face`.
- **Content** — fields that match the element function's parameters.

```typst
#let it = [= Heading]
#it.body          // the body content
#it.depth         // the heading depth field
#it.fields()      // dictionary of all fields
```

## Methods

`value.method(...)` is sugar for `Type.method(value, ...)`. Strings,
arrays, dicts, content all have methods scoped to their type:

```typst
#"abc".len()                   // == #str.len("abc")
#(1, 2, 3).map(x => x * x)     // map is on `array`
```

Mutating methods (`array.push`, `array.pop`, `array.remove`, ...)
**must** be called in method form. Their return value is often `none`
or a removed element; ignore explicitly with `let _ = arr.remove(0)`.

## Modules

Three statements share the same backbone:

| Statement                    | What it does                                                          |
| ---------------------------- | --------------------------------------------------------------------- |
| `include "bar.typ"`          | Evaluate the file, return the resulting `content`. Inserts inline.    |
| `import "bar.typ"`           | Evaluate the file, bind it as a module value (named after the file).  |
| `import "bar.typ" as baz`    | Same, but rename the module.                                          |
| `import "bar.typ": a, b`     | Pull specific bindings (`a`, `b`) into the current scope.             |
| `import "bar.typ": *`        | Pull *all* bindings.                                                  |
| `import "bar.typ": a as one` | Rename per-binding.                                                   |
| `import "bar.typ": baz.a`    | Nested-item import via dot path.                                      |

You can also import from a module *value* you already have:

```typst
#import emoji: face
#face.grin
```

## Packages

Packages live at `@<namespace>/<name>:<version>`. The `preview`
namespace is the community registry on
[Typst Universe](https://typst.app/universe/).

```typst
#import "@preview/example:0.1.0": add
#add(2, 7)
```

Local user packages live under platform-specific paths — see the
[package repository](https://github.com/typst/packages) for details.

## Operators (precedence high → low)

| Op            | Effect                       | Arity   | Precedence |
| ------------- | ---------------------------- | ------- | ---------- |
| `-` (prefix)  | Negation                     | Unary   | 7          |
| `+` (prefix)  | No-op (symmetry)             | Unary   | 7          |
| `*` `/`       | Multiplication / Division    | Binary  | 6          |
| `+` `-`       | Addition / Subtraction       | Binary  | 5          |
| `==` `!=` `<` `<=` `>` `>=` `in` `not in` | Comparison / membership | Binary | 4 |
| `not`         | Logical NOT                  | Unary   | 3          |
| `and`         | Short-circuit AND            | Binary  | 3          |
| `or`          | Short-circuit OR             | Binary  | 2          |
| `=` `+=` `-=` `*=` `/=` | Assignment / compound | Binary  | 1          |

Modulo isn't an operator — use `calc.rem(a, b)` (or `calc.rem-euclid`).

## Practical guidance for an editing assistant

- **Prefer markup for content, code for logic.** Drop into `#` only
  when you have a specific computation; keep prose in markup.
- **Closures over named functions.** When passing a small transform
  (to `map`, `sorted`, `show`), use `it => ...`. Reach for a named
  `let` only when reuse or readability demands it.
- **Destructure aggressively.** It removes index gymnastics and keeps
  intent obvious — especially in iteration over dictionaries and
  arrays of tuples.
- **Don't fight scope.** Prefer scoped set rules in content blocks
  over toggling/restoring values manually. The block boundary is
  the cleanest "undo" you have.
