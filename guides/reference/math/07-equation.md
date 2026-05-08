# `math.equation` — the element behind every `$...$`

`math.equation` is the element produced by writing math between dollar signs. You rarely call it directly; instead, configure it with `set math.equation(...)` or with show rules.

## Parameters

| Param          | Type                                | Default            | Notes                                                                              |
| -------------- | ----------------------------------- | ------------------ | ---------------------------------------------------------------------------------- |
| `block`        | bool                                 | `false`             | Inline (default) vs centered block.                                                |
| `numbering`    | `none` / str / fn(int) → content    | `none`              | Numbering pattern for **block** equations only. Same syntax as [`numbering()`](../model/11-numbering.md). |
| `number-align` | alignment                            | `end + horizon`     | Horizontal: `start`/`end`/`left`/`right`. Vertical: `top`/`horizon`/`bottom`.       |
| `supplement`   | `none` / `auto` / content / fn      | `auto`              | Word prepended in references (e.g. `Equation` / `Eq.`).                            |
| `alt`          | `none` / str                        | `none`              | Natural-language description of the formula for Assistive Technology.              |
| `body`         | content                              | required           | The math content.                                                                  |

## Syntax shortcut

| Syntax            | Equivalent call                                  |
| ----------------- | ------------------------------------------------ |
| `$x^2$`            | `math.equation(block: false, $x^2$)`              |
| `$ x^2 $`          | `math.equation(block: true,  $ x^2 $)`            |

A block equation is triggered by whitespace immediately after the opening `$` AND immediately before the closing `$`.

## Block equations don't break by default

Long derivations are kept on a single page unless you opt in:

```typst
#show math.equation: set block(breakable: true)
```

## Cross-references

`<label>` after a numbered equation makes it referenceable. `@label` then yields, e.g., `Equation (1)` (or `Eq. (1)` if you set `supplement: [Eq.]`).

## Accessibility (`alt`)

Provide a natural-language description so screen readers can read the formula:

```typst
#math.equation(
  alt: "d S equals delta q divided by T",
  block: true,
  $ dif S = (delta q) / T $,
)
```

## Examples (compile-verified)

- `examples/07-equation/01-equation.typ` — numbering, references, `number-align: bottom`, `supplement` override.
- `examples/07-equation/02-breakable-and-alt.typ` — `block(breakable: true)` for long derivations; `alt` for AT.

## Reference

https://typst.app/docs/reference/math/equation/
