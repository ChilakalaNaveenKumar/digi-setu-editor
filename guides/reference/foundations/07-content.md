# Foundations / 07 — `content`

> **Typst version:** 0.14.2
> **Source page:** <https://typst.app/docs/reference/foundations/content/>
> **Audience:** an LLM agent. Original prose; technical facts about the `content` type. All examples below are verified to compile clean with `typst 0.14.2` (see `examples/07-content/`).

---

## Why this page matters

`content` is the central type in Typst. **Every piece of document material — every paragraph, heading, math expression, image, line, page — is a `content` value.** Almost every function the user touches consumes content, returns content, or both.

For an agent editing Typst documents, three concepts are non-negotiable:
1. How content is **produced** (markup `[...]`, element functions, the `+` operator, `* int`).
2. How content is **introspected** (`.func()`, `.fields()`, `.has()`, `.at()`).
3. How content is **transformed** at scale (`set` rules to change defaults, `show` rules to remap rendering).

---

## Producing content

| Source | Result |
|---|---|
| Plain markup written in source | A content sequence of paragraph / text / heading / etc. elements. |
| `[ ... ]` brackets in code mode | Captures the bracketed markup as a `content` VALUE that you can store in a binding or pass around. |
| Calling an element function: `heading("X")`, `rect(...)`, `image("a.png")`, ... | Produces content of that element type. |
| String literal `"..."` where content is expected | Auto-coerced to a single text content. |
| `none` where content is expected | Treated as empty content. |
| `c1 + c2` | Sequence of `c1` followed by `c2`. |
| `c * n` (n is `int`) | Repeats `c` `n` times. |

- **Example:** [`01-constructing-content.typ`](./examples/07-content/01-constructing-content.typ)
- **Example (passing as argument):** [`02-content-as-arg.typ`](./examples/07-content/02-content-as-arg.typ)

---

## Introspecting content

Each content value remembers exactly which **element function** built it (e.g. `heading`, `text`, `rect`) and what **fields** were explicitly set at the call site.

| Method | Returns | Notes |
|---|---|---|
| `c.func()` | `function` | The element function. Compare with `==` against globals: `c.func() == heading`. |
| `c.has("name")` | `bool` | True only if `name` was explicitly passed at construction. **Set-rule defaults do NOT count.** |
| `c.at("name")` | any | Field value. Errors if absent. |
| `c.at("name", default: x)` | any | As above with fallback. |
| `c.fields()` | `dictionary` | All explicitly-passed fields. **Excludes set-rule defaults.** |
| `c.location()` | `location` or `none` | Non-`none` only inside show rules and on results from `query(...)`. Used for counters / state / queries. |

There is also `repr(value)` (top-level builtin, not a method) which returns a `str` showing the internal element structure. Use it as the canonical "what is in this content" debugging hook.

- **Example:** [`03-fields-and-access.typ`](./examples/07-content/03-fields-and-access.typ)
- **Example (`.func()` and show rules):** [`04-func-and-show-rules.typ`](./examples/07-content/04-func-and-show-rules.typ)
- **Example (`repr` as inspector):** [`05-repr-and-introspect.typ`](./examples/07-content/05-repr-and-introspect.typ)

---

## Required vs optional fields (mental model)

| Field kind | Behavior |
|---|---|
| **Required** | Must be passed at the construction site. Always available via `.at(name)` and present in `.fields()` and `.has(name)`. |
| **Optional, explicitly passed** | Available via `.at(name)`, present in `.fields()`, and `.has(name)` is `true`. |
| **Optional, only set by a `set rule`** | NOT available via `.at(name)` / `.fields()` / `.has(name)`. The styling is applied at render time, but the value isn't attached to the element value itself. |

Practical consequence: if you write code that branches on `c.at("inset")`, do NOT assume the styling that comes from `set rect(inset: 8pt)` will appear there. Pass the field explicitly at the call site or compute it yourself.

---

## Set rules and show rules (where this all gets used)

These are detailed in `reference/styling/`, but the agent must remember the connection:

```
// SET: change defaults for all subsequent elements of a kind.
#set heading(numbering: "1.")

// SHOW: completely replace the rendering of all subsequent elements
//       of a kind. The replacement gets the matched content as 'it'.
#show heading: it => [LEVEL #it.level | #it.body]
```

In a show rule, `it` is a `content` value of the matched element kind, with all the introspection methods above available.

---

## Pitfalls (agent-targeted)

1. **`c.fields()` excludes set-rule defaults.** Don't rely on it to discover styling.
2. **`c.at("missing")` errors** without `default:`. Always pass `default:` if the field might not be there.
3. **`+` on content is sequence concatenation, not visual layout.** Use `parbreak()` / `linebreak()` / `pagebreak()` to get explicit breaks.
4. **Multiplication `c * n` requires `n` to be `int`** and `>= 0`.
5. **`c.func() == heading` is the discriminator.** Comparing with strings does not work; compare against the actual function value.
6. **`c.location()` is `none` outside of show rules / query results.** Don't try to use it on freshly-constructed content for counters.
7. **Inside a show rule, returning `it` produces an infinite loop** — the same element keeps matching. To "fall through" without modifying, return a *different* element, or guard with `if`.

---

## Self-check

1. To capture markup as a value, did you wrap it in `[ ... ]`?
2. To pass a field that should be discoverable later via `.fields()`, did you pass it at the call site (not via `set`)?
3. When testing element kind, are you using `c.func() == heading` (function value) and not `"heading" in str(c.func())`?
4. When defaulting a possibly-missing field, did you pass `default: ...` to `.at()`?
5. Inside a show rule, are you guarding against re-matching the same element?
6. Does it compile? (`typst compile path.typ /tmp/out.pdf`)
