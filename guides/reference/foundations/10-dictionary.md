# Foundations / 10 — `dictionary`

> **Typst version:** 0.14.2
> **Source page:** <https://typst.app/docs/reference/foundations/dictionary/>
> **Audience:** an LLM agent. Original prose; technical facts about the `dictionary` type. All examples below are verified to compile clean with `typst 0.14.2` (see `examples/10-dictionary/`).

---

## What it is

A `dictionary` is an ordered map from **string** keys to values of any type. Values within a single dictionary may be heterogeneous (mixed types). Insertion order is preserved across iteration, `keys()`, `values()`, and `pairs()`.

---

## Construction (and a famous gotcha)

| Form | Result |
|---|---|
| `(name: "Typst", born: 2019)` | dictionary with two keys |
| `(:)` | empty dictionary |
| `()` | **empty ARRAY** — NOT a dictionary. Surprising but consistent. |
| `("strkey": 1)` | dictionary with a string-literal key (useful when the key isn't a valid identifier) |

- **Example:** [`01-construct-and-access.typ`](./examples/10-dictionary/01-construct-and-access.typ)

---

## Accessing values

| Syntax | When to use |
|---|---|
| `dict.key` | Static key that is a valid identifier. |
| `dict.at("key")` | Dynamic / computed key, OR keys that aren't valid identifiers. |
| `dict.at("key", default: x)` | Dynamic key with safe fallback. |
| `"key" in dict` | Membership test → `bool`. |

---

## Mutation

| Operation | Notes |
|---|---|
| `dict.key = v` | Field-style assignment. **Key must already exist.** Use `insert` to add. |
| `dict.insert("k", v)` | Adds (or overwrites) a key. Always works. |
| `dict.remove("k")` | Returns the removed value. **Errors if key absent.** |
| `dict.remove("k", default: x)` | Returns `x` if key absent. |
| `dict += other_dict` | In-place merge, last-wins on duplicates. |

---

## Methods

| Method | Returns | Notes |
|---|---|---|
| `dict.len()` | `int` | Number of key-value pairs. |
| `dict.at(key)` / `dict.at(key, default: x)` | any | See above. |
| `dict.insert(key, value)` | none | See above. |
| `dict.remove(key)` / `dict.remove(key, default: x)` | any | See above. |
| `dict.keys()` | `array` of `str` | In insertion order. |
| `dict.values()` | `array` of any | In insertion order. |
| `dict.pairs()` | `array` of `[key, value]` | Each pair is itself a 2-element array. |

- **Example (iteration):** [`02-iteration-keys-values-pairs.typ`](./examples/10-dictionary/02-iteration-keys-values-pairs.typ)

---

## Merging & spread

| Form | Behavior |
|---|---|
| `a + b` | New dictionary, keys from `b` override duplicates from `a`. |
| `(:..a, ..b)` | Same effect via spread. **NOTE:** when EVERY item is a spread, the leading `:` is REQUIRED — without it the parser sees an array literal and errors with `cannot spread dictionary into array`. |
| `(key: v, ..base)` | Mixed: regular `()` is fine because the literal `key: v` disambiguates. |
| Spreading into a function call: `f(..dict)` | Each pair becomes a NAMED argument at the call site. |

- **Example:** [`03-merge-spread-and-default.typ`](./examples/10-dictionary/03-merge-spread-and-default.typ)

---

## Pitfalls (agent-targeted)

1. **`()` is an empty array, NOT an empty dictionary.** Use `(:)` for an empty dict.
2. **`(..a, ..b)` errors** if all items are spreads. Use `(:..a, ..b)`.
3. **Field-assign `dict.key = v` fails on a missing key.** Use `dict.insert("key", v)` to add.
4. **`dict.remove("k")` errors on missing key** unless `default:` is given.
5. **`dict.at("k")` errors on missing key** unless `default:` is given. For tolerant lookup, prefer `at(..., default: ...)`.
6. **Keys are always strings.** You cannot use ints, content, or other types as keys.
7. **Duplicate keys in a literal** silently keep only the last one — they don't error.

---

## Self-check

1. Did you use `(:)` and not `()` for an empty dict?
2. When merging via spread, did you remember the `:` prefix in the all-spread case?
3. When reading possibly-missing keys, did you pass `default:` to `at()` / `remove()`?
4. When iterating, did you destructure with `for (k, v) in dict.pairs() { ... }` (not `for k in dict { ... }` — that doesn't work)?
5. Does it compile? (`typst compile path.typ /tmp/out.pdf`)
