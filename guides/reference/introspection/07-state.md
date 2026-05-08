# `state` — Per-Document Mutable State

`state` is Typst's general-purpose state container. It mirrors `counter`
but holds **arbitrary values** (strings, dictionaries, content, ...)
instead of integer arrays.

## Why state? Why not `let`?

Because document evaluation isn't sequential. Show rules, templates, and
introspection make Typst process content out of layout order. A plain
mutable `let` cannot guarantee values are read in the same order they
are laid out, so Typst forbids it. State, by contrast, threads through
the document in **layout order** — guaranteeing predictable results.

## Constructing

```typst
#let chapter = state("chapter", "")          // key + initial value
#let banner  = state("banner", none)
```

If multiple `state(key, ...)` calls share the same key but different
initial values, each starts with its own initial value but they share
updates.

## Methods

### Read (need `context`)

| Method                | Returns                                  |
| --------------------- | ---------------------------------------- |
| `s.get()`             | Value at the current location.           |
| `s.at(selector)`      | Value at the matched location.           |
| `s.final()`           | Value at the end of the document.        |

### Modify (no `context` needed; produces invisible content)

| Method                  | Effect                                                         |
| ----------------------- | -------------------------------------------------------------- |
| `s.update(value)`       | Set state to `value` at the placement position.                |
| `s.update(prev => new)` | Function form — preferred, fewer iterations, more predictable. |

The update only takes effect **at the position** where its returned
content is inserted. `let _ = s.update(...)` does nothing.

## Pattern: "current chapter" header

```typst
#let chapter = state("chapter", "")

#show heading.where(level: 1): h => {
  chapter.update(h.body)
  h
}

#set page(header: context align(right, emph(chapter.get())))

= Introduction
…
= Methods
…
```

This is the same idea as the [LaTeX `\mark`](https://en.wikibooks.org/wiki/LaTeX/Page_Layout#Marks)
mechanism — the page header always reflects the most recent level-1
heading.

## Pattern: accumulating computation

```typst
#let star = state("star", 0)
#let compute(expr) = {
  star.update(prev => eval(expr.replace("⭐", str(prev))))
  [New value: #context star.get(). \ ]
}

#compute("10")        // 10
#compute("⭐ + 3")    // 13
#compute("⭐ * 2")    // 26
#compute("⭐ - 5")    // 21
```

State updates apply in **layout order**, so even if you store the
intermediate calls in a variable and insert them later, the values still
chain correctly.

## Time travel

```typst
#let s = state("counter", 0)
#context [
  At <here-label>: #s.at(<here-label>) \
  Final value:    #s.final()
]
…body that updates s…
*Marker.* <here-label>
```

`.at(loc)` and `.final()` make state queryable at any moment in the
document — which is what powers things like the page numbering display
("page 3 of 17").

## Pitfalls

- **Don't update state from a context that depends on the same state's
  final value.** This produces a feedback loop; Typst gives up after a
  few iterations and you get unstable output.
- **Use the function form of `update`.** `s.update(prev => prev + 1)`
  resolves more predictably than `context s.update(s.get() + 1)` — the
  former takes one iteration, the latter may take several.
- State updates that aren't placed in the document do nothing. Make
  sure the result is included as content (e.g. by sitting on its own at
  the top level of a code block).
