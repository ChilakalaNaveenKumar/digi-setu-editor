# Making a Template

A Typst **template** is just a function that takes the document's
content (and any configuration) and returns styled content. Wrap your
document in it with an "everything" show rule and you have a
reusable, sharable layout.

## Variables come first

Before talking about templates, recognize that ordinary variables
already remove a lot of repetition. `let` works for any value —
content, strings, numbers, lengths, ratios, alignments, even
functions:

```typst
#let ipa = text(style: "italic")[/taɪpst/]
The pronunciation is #ipa.
```

Reasons to extract a value into a variable:

- It's used in multiple places (change once, change everywhere).
- It's hard to type or visually noisy (long strings, IPA, math).
- The name documents the intent better than the literal.
- You want a single place to swap implementations later.

Things you can store in variables (illustrative):

| Type      | Example                                |
| --------- | -------------------------------------- |
| content   | `#let blind = [_Lorem ipsum_]`         |
| string    | `#let font-name = "MS Comic Sans"`     |
| length    | `#let mile = 160934cm`                 |
| em-length | `#let double-space = 2em`              |
| ratio     | `#let progress = 80%`                  |
| integer   | `#let answer = 42`                     |
| boolean   | `#let truth = false`                   |
| alignment | `#let focus = center`                  |
| function  | `#let amazed(t) = box[✨ #t ✨]`        |

## Custom functions

A `let` with parentheses on the left-hand side defines a function:

```typst
#let amazed(term) = box[✨ #term ✨]
You are #amazed[beautiful]!
```

Inside a function the body can be markup or code. Use `box` to keep
markup on a single visual line where appropriate. Functions with
named parameters and defaults look like this:

```typst
#let amazed(term, color: blue) = {
  text(color, box[✨ #term ✨])
}
You are #amazed[beautiful]!
I am #amazed(color: purple)[amazed]!
```

## Everything-show rule = "wrap the document"

A show rule with no selector — `#show: function` — passes the
**rest of the document** to the function as a single content
argument. The function's return value becomes the document.

```typst
#show: amazed
I am amazing!
```

This is the canonical way to apply a template without manually
wrapping the whole body in a giant function call.

## A "real" template function

Move all the conference-paper styling into a single function. Use
**curly-brace code blocks** instead of square-bracket content blocks
so that you can write `set text(...)` directly without `#`:

```typst
#let conf(title, doc) = {
  set page(
    paper: "us-letter",
    header: align(right + horizon, title),
    columns: 2,
    numbering: "1",
  )
  set par(justify: true)
  set text(font: "Libertinus Serif", size: 11pt)

  show heading.where(level: 1): set align(center)
  show heading.where(level: 1): set text(size: 13pt, weight: "regular")
  show heading.where(level: 1): smallcaps

  show heading.where(level: 2): set text(
    size: 11pt, weight: "regular", style: "italic",
  )
  show heading.where(level: 2): it => it.body + [.]

  doc                     // emit the body LAST
}

#show: doc => conf([Paper title], doc)

= Introduction
...
```

Two things to notice:

- The template function ends by emitting `doc` — without that the
  body never appears.
- `#show: doc => conf(...)` uses an inline closure because the
  template's first argument is a title. The everything-show rule
  passes only one argument (the body), so the closure plugs the
  title in.

## Named arguments and defaults

Real templates take *configuration*. Add named parameters with
defaults so callers can opt in:

```typst
#let conf(
  title: [Untitled],
  authors: (),
  abstract: [],
  doc,
) = {
  set page(...)
  set par(justify: true)
  set text(font: "Libertinus Serif", size: 11pt)
  ...

  place(
    top + center, float: true, scope: "parent", clearance: 2em,
    {
      title

      let count = authors.len()
      let ncols = calc.min(count, 3)
      grid(
        columns: (1fr,) * ncols,
        row-gutter: 24pt,
        ..authors.map(a => [
          #a.name \
          #a.affiliation \
          #link("mailto:" + a.email)
        ]),
      )

      par(justify: false)[
        *Abstract* \
        #abstract
      ]
    },
  )

  doc
}
```

Key techniques:

- `(1fr,) * ncols` builds an array of `ncols` equal-fraction
  columns by **multiplying** a single-element tuple. Faster and
  clearer than building a literal each time.
- `authors.map(a => [...])` produces an array of content values, one
  per author.
- `..authors.map(...)` **spreads** that array as positional arguments
  to `grid` — exactly what's needed.
- `calc.min(count, 3)` caps the number of columns at three, so a
  fourth author wraps to a new row instead of cramming in.

## Apply the template (caller side)

```typst
#show: doc => conf(
  title: [A Fluid Dynamic Model for Glacier Flow],
  authors: (
    (name: "Theresa Tungsten", affiliation: "Artos Institute",
     email: "tung@artos.edu"),
    (name: "Eugene Deklan",    affiliation: "Honduras State",
     email: "e.deklan@hstate.hn"),
  ),
  abstract: lorem(80),
  doc,
)

= Introduction
...
```

## Move the template to a separate file

Real templates live in their own `.typ` file so the user's document
stays clutter-free.

`conf.typ`:

```typst
#let conf(title: [Untitled], authors: (), abstract: [], doc) = { ... }
```

`paper.typ`:

```typst
#import "conf.typ": conf

#set document(title: [A Fluid Dynamic Model for Glacier Flow])

#show: conf.with(
  authors: (
    (name: "Theresa Tungsten", ...),
    (name: "Eugene Deklan",    ...),
  ),
  abstract: lorem(80),
)

= Introduction
...
```

The `.with(...)` method **partially applies** a function — it
returns a new function with the given named arguments pre-filled.
Combined with the everything-show rule, you get the cleanest
possible template invocation: the show rule just passes the body in,
and `.with(...)` already supplied everything else.

This same pattern is what every template on
[Typst Universe](https://typst.app/universe/) uses. To publish your
own:

1. Move the template into its own package directory with a
   `typst.toml`.
2. Pick a function signature that takes named config + a final
   `doc` parameter.
3. Document the parameters in a README.
4. Submit to the [packages](https://github.com/typst/packages) repo.

## Mental model recap

- A template is **just a function**. There's no special "template"
  type or registration.
- Wrap your document with `#show: my-template.with(...)` (preferred)
  or `#show: doc => my-template(args, doc)` (if you can't use
  `.with`).
- `set` rules inside the template are scoped to the body the
  template returns — exactly what you want.
- Use **show-set** rules in templates (rather than full
  transformational show rules) wherever possible, so the user can
  still tweak details from their document.
- Organize templates so the *user's* document only contains content
  and the *template* contains layout. That's it.
