# `type` — runtime type values

`type(value) -> type` returns the type of any value. The returned object **is** the type — you compare it directly:

```typst
#if type(x) == int [ ... ]
```

Typst's types are first-class values; you can pass them around, compare them, store them in dictionaries.

## Common type names

| Value                  | `type(...)` returns         |
| ---------------------- | --------------------------- |
| `12`                   | `integer`                   |
| `14.7`                 | `float`                     |
| `"hello"`              | `string`                    |
| `<glacier>`            | `label`                     |
| `[Hi]` or any markup   | `content`                   |
| `(1, 2, 3)`            | `array`                     |
| `(a: 1)`               | `dictionary`                |
| `x => x + 1`           | `function`                  |
| `image("...")` element | `content` (see caveat below)|
| `int`                  | `type`                      |
| `type`                 | `type`                      |

## Two big gotchas

### 1. All elements are `content`

```typst
#type([= My Heading])  // -> content
#type([Just a para.])  // -> content
#type([- one
- two])                // -> content
```

To **distinguish** which kind of element you have, use `.func()`:

```typst
#let h = [= Heading]
#h.func() == heading   // -> true
```

This is the standard pattern inside show-rule handlers that take generic `content` and need to dispatch.

### 2. `none` and `auto` have no name binding

You cannot write `type(x) == none-type`. There's no name for either type. Test the value directly:

```typst
#if val == none [ ... ]
#if val == auto [ ... ]
```

## When to reach for `type`

- **Polymorphic helpers** that accept either a string or a content value:
  ```typst
  #let title(t) = if type(t) == str { strong(t) } else { strong(t) }
  ```
- **Defensive parameter validation** (combine with `assert`):
  ```typst
  #let scale(v, factor) = {
    assert(type(v) == int or type(v) == float, message: "v must be numeric")
    v * factor
  }
  ```
- **Debug printing**:
  ```typst
  #let dbg(x) = [#repr(x) (#type(x))]
  ```

## Pitfalls

- **`type(x) == content` is almost always true** for anything coming from markup. Use `.func()` for finer-grained dispatch.
- **Don't store the `type` of `none` / `auto` and try to compare** — comparing `value == none` works; trying to derive a type sentinel from a none value gives you `none`'s sentinel that won't match other none values predictably across versions.
- **Type names print in their full English form** (`integer`, not `int`) when inserted into content. The bareword identifiers (`int`, `float`, `str`) are the *bindings*; in code, `type(10) == int` is true.

## Examples (compile-verified)

- `examples/29-type/01-type-of-various.typ` — `type` of every common value, dispatch with `==`, `none`/`auto` value-comparison pattern.
- `examples/29-type/02-content-func-vs-type.typ` — every element returns `content`; `.func()` differentiates heading / par / list and lets you compare against `heading`, `list`, etc.

## Reference

- Official: https://typst.app/docs/reference/foundations/type/
- `content.func`: https://typst.app/docs/reference/foundations/content/#definitions-func
