# Styling – Set Rules and Show Rules

Typst's styling system has two pieces. **Set rules** change the
*default arguments* of an element. **Show rules** change *how an
element is rendered*. Together they let you go from "tweak the
title font" to "completely re-skin every level-2 heading", with the
same syntax.

## Set rules

A set rule is an [element function](./foundations/14-function.md#element-functions)
preceded by `set` (or `#set` in markup). It only accepts that
function's *optional* parameters, and acts like changing the defaults
for every following call to that function:

```typst
#set heading(numbering: "I.")
#set text(font: "New Computer Modern")

= Introduction
With set rules, you can style your document.
```

A top-level set rule stays in effect until **end of file**. Inside a
block (`{ ... }`) or content block (`[ ... ]`) it stays in effect
until **end of that block** — perfect for scoping a style change to a
single piece of content:

```typst
This list is affected: #[
  #set list(marker: [--])
  - Dash
]

This one is not:
- Bullet
```

### Conditional set rules (`set ... if`)

Use `set ... if condition` to apply a set rule only when a predicate
is true. Common pattern: tag-based styling for "critical" items.

```typst
#let task(body, critical: false) = {
  set text(red) if critical
  [- #body]
}

#task(critical: true)[Food today?]
#task(critical: false)[Work deadline]
```

## Show rules

A show rule replaces the rendered appearance of *matching elements*.
General syntax:

```text
#show <selector>: <replacement>
```

The `<selector>` says **what to match**, the `<replacement>` says
**what to do** with it.

### Show-set rules

The simplest replacement is another `set` rule. This style adjusts
*only* the matched elements:

```typst
#show heading: set text(navy)

= This is navy-blue
But this stays black.
```

Show-set rules **compose** — pile them up to mix and match
properties from different functions:

```typst
#show heading: set align(center)
#show heading: set text(font: "Inria Serif")
#show heading: set block(above: 1.4em, below: 0.8em)
```

This is the most maintainable form of show rule — the resulting
element still respects later show-set overrides, so templates stay
flexible.

### Transformational show rules

When a show-set isn't enough, replace the right-hand side with a
function. The function receives the matched element as `it` (any
parameter name works) and returns the new content:

```typst
#show heading: it => block[
  \~
  #emph(it.body)
  #counter(heading).display(it.numbering)
  \~
]
```

The `it` value is the element itself — its fields (`it.body`,
`it.level`, `it.numbering`, ...) are the same as the element's
constructor parameters. See [`content`](./foundations/07-content.md)
for the field model.

> **Trade-off.** Once you write a transformational show rule for an
> element, later show-set rules on that element won't apply — they
> would have applied to the original `it`, but you've replaced it with
> custom layout. Reach for show-set first, transformational only when
> needed.

### Other right-hand sides

| RHS                           | Effect                                                 |
| ----------------------------- | ------------------------------------------------------ |
| Another set rule              | Show-set: only matching elements get the new defaults. |
| A function (`it => ...`)      | Transformational: replace with arbitrary content.      |
| A literal string `"replacement"` | Substitute matching text/element with the string.   |
| A literal content block `[...]` | Substitute matching element with that content.       |

```typst
#show "Project": smallcaps     // function used as transform
#show "badly": "great"         // literal-string replacement

We started Project in 2019.
It is progressing badly.
```

## Selectors

The left-hand side of a show rule (and the argument to the
`selector(...)` constructor) describes **what to match**.

| Selector form                                    | Matches                                            |
| ------------------------------------------------ | -------------------------------------------------- |
| Element function: `heading`                      | Every heading.                                     |
| Filtered element: `heading.where(level: 1)`      | Only first-level headings.                         |
| Label: `<intro>`                                 | Every element carrying that label.                 |
| Text literal: `"Project"`                        | Every occurrence of that string in the body.       |
| Regex: `regex("\d+")`                            | Every regex match in body text.                    |
| Whole document: `:` (no LHS, e.g. `#show: f`)    | The remainder after this rule (everything-show).   |

Combine with [selector combinators](./foundations/23-selector.md)
(`.before(loc)`, `.after(loc)`, `.or(other)`) for query-style
filtering:

```typst
#show heading.where(level: 1).or(heading.where(level: 2)): set text(navy)
```

## "Everything" show rule

`#show: function` (no selector before the colon) wraps the rest of
the document in `function(rest_of_document)`. This is how *templates*
work:

```typst
#show: my-template.with(title: "Annual Report")
... rest of the document ...
```

The everything-show rule is the canonical way to apply a template
without manually wrapping the whole document body in `function([ ... ])`.

## Set vs show vs styled element

| Goal                                                       | Use                                                       |
| ---------------------------------------------------------- | --------------------------------------------------------- |
| One-off styled span                                        | `#text(weight: "bold")[bold]`                             |
| Change defaults for the rest of the block                  | `#set text(weight: "bold")`                               |
| Match a particular subset of elements                      | `#show heading.where(level: 1): set text(navy)`           |
| Completely replace the rendering                           | `#show heading: it => block[...custom layout...]`         |
| Apply a template to the whole document                     | `#show: tpl.with(...)`                                    |

## Scope rules

- A set/show rule applies from where it appears to the end of the
  containing block (or file if at top level).
- Set rules **scope by content block** — `#[ #set ... ; ... ]` only
  affects what's inside the brackets.
- Inside a transformational show rule, set rules act on the **content
  the function returns**, not on the whole document. Prefer show-set
  rules for things that should remain externally overridable.

## Composition rules

- Multiple set rules on the same parameter — the later one wins inside
  its scope.
- Multiple show rules on the same selector — they apply outside-in
  (the most recently written rule sees the result of earlier ones).
  This means `#show heading: smallcaps` followed by `#show heading: set
  align(center)` first runs alignment, then small-caps.
- A show-set rule preserves the element's identity — later show rules
  still match it. A transformational show rule replaces the element,
  so further show rules on that element function don't trigger.
