# `counter` — Counters

`counter` lets you read, modify, and time-travel through any of Typst's
built-in counters (page, heading, figure, math.equation, footnote) or
custom counters keyed by string.

## Constructing

```typst
#let mine = counter("mycounter")             // custom, keyed by string
#counter(page)                                // built-in page counter
#counter(heading)                             // built-in heading counter
#counter(figure.where(kind: image))           // figures of a specific kind
#counter(<my-label>)                          // counts elements with label
```

The `key` may be:

- A string — defines a fresh custom counter (or refers to an existing one
  with the same string).
- A `selector` (element function, `where(...)`, label) — counts elements
  matching that selector. The element type must be locatable.

## Methods

### Read (need `context`)

| Method                 | Returns                                                     |
| ---------------------- | ----------------------------------------------------------- |
| `c.get()`              | Array of integers — the value at the current location.      |
| `c.at(selector)`       | Array — the value at the matched location.                  |
| `c.final()`            | Array — the value at the end of the document.               |
| `c.display(numbering: auto, both: false)` | Formatted string content.                |

A counter value is **always an array** (e.g. `(2, 3, 1)` for a 3-level
heading counter) even if it's logically just one number.

### Modify (no `context` needed; produces content)

| Method                       | Effect                                              |
| ---------------------------- | --------------------------------------------------- |
| `c.step(level: 1)`           | Increment by 1 at the given depth.                  |
| `c.update(value)`            | Set to a number/array.                              |
| `c.update(prev => new)`      | Function form — preferred for derived updates.      |

The update only takes effect **at the position** where its returned
content is placed. `let _ = c.step()` does nothing.

## Counters always start at zero

Built-in counters (heading, figure, etc.) are stepped **before** the
counted element shows up, so the first display reads `1`. Custom counters
should follow the same convention: step first, then display.

```typst
#let c = counter("theorem")
#let theorem(it) = block[
  #c.step()
  *Theorem #context c.display():* #it
]
#theorem[$1 = 1$]
#theorem[$2 < 3$]
```

## Page counter

The page counter is special: it auto-steps at every page break. You can
still step or reset it manually for prefaces, appendices, etc.:

```typst
#set page(numbering: "(i)")
= Preface
…
#set page(numbering: "1 / 1")
#counter(page).update(1)             // restart numbering at 1
= Main text
```

`numbering: "1 / 1"` is a hint to display *both* the current value and
the final value — `display(both: true)` does the same thing in custom
templates.

## `display(numbering: ...)` patterns

`display()` formats with the counter's element-typical pattern (or `"1.1"`
fallback). Override with any `numbering` pattern or function:

```typst
#context counter(heading).display("I.A.1")     // Roman . letter . arabic
#context counter(heading).display(nums => nums.map(str).join(":"))
```

For the heading counter (which can have variable depth), receive `..nums`
in your function: `(..nums) => nums.pos().map(str).join(".")`.

## Time travel

```typst
#context [
  Final number of theorems: #counter("theorem").final().first()
  Theorems before <intro>: #counter("theorem").at(<intro>).first()
]
```

Useful for "appears X times" summaries, cross-references that resolve to
different counts depending on document position, and reverse-numbered
listings.

## Counters vs state

Counters are integer arrays optimized for the "step + display" pattern.
For arbitrary values (text, content, dictionaries) reach for
[`state`](./07-state.md). Both share the same time-travel guarantees.
