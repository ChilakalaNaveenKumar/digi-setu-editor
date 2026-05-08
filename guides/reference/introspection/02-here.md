# `here()` — Current Location

`here()` returns the [`location`](./04-location.md) of the *current
context's* position in the document. It's a low-level building block — most
higher-level functions (`counter.get`, `state.get`, etc.) call it for you.

## Signature

```text
here() -> location
```

`here()` is **contextual** — call it inside a `context { ... }` block (or
`#context [...]`) so Typst knows where "here" is.

Inside a show rule on a [locatable element](./00-introspection-overview.md#locatable-elements),
`here()` resolves to the location of the matched element.

## Common uses

### What page am I on?

```typst
#context [I'm on page #here().page().]
```

`.page()` gives you the **physical** page number (always starts at 1),
ignoring `set page(numbering: ...)`. For the *displayed* page number,
read `counter(page).at(here())`.

### Where on the page am I?

```typst
#context [
  Position: #here().position()    // (page: ..., x: ..., y: ...)
]
```

### Counters and state at the current spot

`counter(heading).get()` is sugar for `counter(heading).at(here())`.

### Anchored queries — "before me", "after me"

```typst
There are
#context query(selector(heading).before(here())).len()
headings before this point.
```

See [`selector`](../foundations/19-selector.md) for `.before()` /
`.after()` modifiers.

## Pitfalls

- Outside `context` blocks, calling `here()` errors: "the type 'function'
  has no method 'here'" or similar — Typst doesn't know what location to
  use.
- `here()` inside a show rule on a non-locatable element returns the
  surrounding context's location, not the element's location.
