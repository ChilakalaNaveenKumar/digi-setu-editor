# Foundations / 14 — `function`

> **Typst version:** 0.14.2
> **Source page:** <https://typst.app/docs/reference/foundations/function/>
> **Audience:** an LLM agent. Original prose; technical facts about the `function` type. All examples below are verified to compile clean with `typst 0.14.2` (see `examples/14-function/`).

---

## Why this page matters

Functions are the dominant verb in Typst. Every styling change, every layout adjustment, every dynamic computation routes through a function call. For an agent editing Typst, mastering call-site forms, definition forms, and the `with` / `where` family is essential.

There are two flavors of function value, both of type `function`:
- **Pure user functions** — defined with `let f(...) = ...`. Take args, return values. Cannot appear in `set` / `show` rule targets.
- **Element functions** — built-in functions like `heading`, `text`, `rect`. They produce `content` of their respective element kind AND act as targets in `set` / `show` rules and selectors.

---

## Calling a function

Three call-site syntaxes:

```
// 1. Standard call
f(p1, p2, name1: v1, name2: v2)

// 2. Trailing content blocks (each [..] is one extra positional arg)
f(name: v)[content1][content2]

// 3. No-paren shorthand: when the only args are trailing content blocks
f[content1][content2]
```

Rules:
- All positional arguments come before all named arguments.
- Trailing content blocks always count as **positional** args, after any explicit positionals.
- Spread operands (`..value`) are allowed at any position; see the `arguments` page.

- **Example:** [`01-call-syntax.typ`](./examples/14-function/01-call-syntax.typ)

---

## Defining a function

```
let f(p1, p2: default, ..rest) = body
```

| Element | Notes |
|---|---|
| `p1` | Positional, required. |
| `p2: default` | Named with default; caller may omit. |
| `..rest` | Argument sink, must be LAST. Captures excess positional and named args as an `arguments` value. |
| `body` | Any expression. If a code block `{ ... }`, the return value is the joined value of all top-level expressions in the block. |

`return [value]` exits early. If no value is supplied, returns `none` (well: the joined value of all expressions evaluated before the `return`).

### Anonymous (arrow) functions

```
let double = x => x * 2          // single param: parens optional
let add = (a, b) => a + b
let sum = (..nums) => nums.pos().sum()
```

Anonymous functions are mainly for show rules and for parameters that take callbacks (e.g. `page(footer: it => ...)`).

- **Example:** [`02-defining-functions.typ`](./examples/14-function/02-defining-functions.typ)

---

## Purity

All user-defined functions are **pure**: same inputs, same outputs, no side effects. Functions cannot remember state across calls.

The only exceptions are built-in mutating methods like `array.push(value)` — they modify the value they're called on. User code cannot do this.

If you need accumulating state across the document (e.g. "section number"), use the `state` and `counter` introspection types in `reference/introspection/`.

---

## Methods on `function`

### `f.with(...args) -> function`

Returns a new function with the given args **pre-applied**. Partial application / currying.

```
let bold-red = text.with(fill: red, weight: "bold")
#bold-red[Highlighted phrase]
```

- **Example:** [`03-with-partial-application.typ`](./examples/14-function/03-with-partial-application.typ)

### `element_function.where(field: v, ...) -> selector`

Available on **element functions only**. Produces a `selector` that matches elements of that kind whose explicitly-set fields equal the given values. Use as the target of a `show` rule or in `query(...)`.

```
#show heading.where(level: 2): set text(blue)
```

- **Example:** [`04-where-selector.typ`](./examples/14-function/04-where-selector.typ)

---

## Importing functions from other files

```
#import "helpers.typ": alert, format
#import "helpers.typ": *           // import everything
#import "helpers.typ" as h         // import as a module value
```

Then use `alert[…]` directly, or `h.alert[…]`.

---

## Element functions vs pure functions (the discriminator)

| Capability | Element function (e.g. `heading`) | User function (e.g. `let f(x) = …`) |
|---|---|---|
| Callable | yes | yes |
| Returns content | yes (always) | depends on body |
| Usable in `set <fn>(...)` rule | yes | no |
| Usable as `<fn>` in `show <fn>: ...` | yes | no |
| `<fn>.where(field: v)` | yes | no |
| `<fn>.with(...)` | yes | yes |
| Comparable via `c.func() == <fn>` | yes (`c.func() == heading`) | n/a (user fns don't appear in content) |

---

## Pitfalls (agent-targeted)

1. **Argument sink `..rest` must be last in the param list.**
2. **Named args go after positional args at the call site.** `f(name: v, positional)` is a syntax error.
3. **Trailing content blocks count as positional.** `f(p1)[A]` passes `p1` and `[A]` as the first two positional args.
4. **`set` / `show` rules need element functions, not user functions.** `set my-helper(...)` is a type error.
5. **Anonymous-function single-param parens are optional but adding parens is harmless** and aids readability: prefer `(x) => x * 2` if `x` is short and one-letter.
6. **`return` without a value returns `none`,** not "the body so far". (Actually, the body so far IS joined first, then `return` happens — but this is a subtle point; if you mean to exit and return a value, write `return value` explicitly.)
7. **Functions are pure.** Don't try to track state across calls; reach for `state`/`counter` instead.

---

## Self-check

1. At call sites, are positional args before named args?
2. In definitions, is `..rest` (if present) the last parameter?
3. For partial application, did you use `f.with(...)` (returns a new function) instead of trying to call it half-applied?
4. For show-rule targets that need to filter by field, did you reach for `element.where(field: v)`?
5. For state across calls, are you using `state`/`counter` (not closures over mutable variables, which don't work)?
6. Does it compile? (`typst compile path.typ /tmp/out.pdf`)
