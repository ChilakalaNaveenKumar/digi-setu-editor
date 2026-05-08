# `location` — Element Locations

A `location` uniquely identifies an element in the laid-out document. It's
what you get back from `here()`, `locate(...)`, and `(content).location()`
on a queried element.

## Where locations come from

| Source                                | Returns                                              |
| ------------------------------------- | ---------------------------------------------------- |
| `here()`                              | Current location (in `context`).                     |
| `locate(<label>)`                     | The unique matching element's location.              |
| `query(...).map(e => e.location())`   | Every matched element's location.                    |
| `e.location()` (where `e` is content) | The element's location, if locatable.                |

## Methods

| Method                | Returns                                                                                  |
| --------------------- | ---------------------------------------------------------------------------------------- |
| `loc.page()`          | **Physical** page number (1, 2, ...). Ignores any custom page numbering reset.           |
| `loc.position()`      | Dictionary `(page: int, x: length, y: length)` from the top-left of the page.            |
| `loc.page-numbering()`| The numbering pattern that was active at this location (`none` if numbering is off).     |

## Reading counters/state at a location

```typst
#counter(page).at(loc)         // displayed page number at loc
#counter(heading).at(loc)      // heading counter at loc
#state("chapter").at(loc)      // your custom state at loc
```

These are how you build TOCs, indices, and "as of page N" snippets.

## Recipe: page label that follows the active numbering pattern

```typst
#context [
  See <intro> on page
  #numbering(
    locate(<intro>).page-numbering(),
    ..counter(page).at(locate(<intro>)),
  )
]
```

This applies the numbering pattern **active at the target location** to
the page-counter value at that location — the exact behavior of the
built-in `outline` for tables of contents.

## Locatable elements

Only locatable elements have a stable location. Concrete list:

- **Always locatable**: most `model` elements (`heading`, `figure`,
  `outline`, `bibliography`, `quote`, `cite`, `terms.item`, `enum.item`,
  `list.item`), `metadata`, `math.equation`, `image`.
- **Locatable**: `raw`, `underline`, `overline`, `strike`, `highlight`.
- **Not locatable** (use a `<label>`): plain text, `text`, `box`, `block`,
  `align`, `pad`, `place`, ...

If you label a non-locatable element, the *labelled element* becomes
queryable but its `.location()` may not return what you expect for
positioning — the label and the element share the same location only when
the underlying element is locatable.
