# Foundations / 08 — `datetime`

> **Typst version:** 0.14.2
> **Source page:** <https://typst.app/docs/reference/foundations/datetime/>
> **Audience:** an LLM agent. Original prose; technical facts about the `datetime` type. All examples below are verified to compile clean with `typst 0.14.2` (see `examples/08-datetime/`).

---

## What it is

`datetime` represents one of three things, depending on which fields you pass at construction:

| Fields supplied | Stored as | Component methods that return non-`none` |
|---|---|---|
| `year` + `month` + `day` | **date only** | `.year()`, `.month()`, `.day()`, `.weekday()`, `.ordinal()` |
| `hour` + `minute` + `second` | **time only** | `.hour()`, `.minute()`, `.second()` |
| All six | **full datetime** | All of the above |

For unsupplied components the corresponding method returns `none`.

---

## Constructor

```
datetime(
  year:   int,
  month:  int,    // 1..12
  day:    int,    // 1..31 (validated against month/year)
  hour:   int,    // 0..23
  minute: int,    // 0..59
  second: int,    // 0..59
) -> datetime
```

All parameters are **named**. Pass the subset you need (per the table above).

---

## `datetime.today(offset: auto)`

Returns the current local date.

| `offset` value | Meaning |
|---|---|
| `auto` (default) | Use the local timezone offset. |
| integer (e.g. `0`, `-5`) | Treat as hours offset from UTC. |

For reproducible / CI builds, override the "current time" via the CLI flag `--creation-timestamp <unix-ts>` or the env var `SOURCE_DATE_EPOCH=<unix-ts>`.

- **Example:** [`02-fields-and-today.typ`](./examples/08-datetime/02-fields-and-today.typ)

---

## `.display(pattern: auto | str)`

Formats the value as a `str`. If `pattern` is `auto`, the default depends on what's stored:

| Stored kind | Default pattern |
|---|---|
| date | `[year]-[month]-[day]` |
| time | `[hour]:[minute]:[second]` |
| full datetime | `[year]-[month]-[day] [hour]:[minute]:[second]` |

A custom pattern is a string with `[component]` tokens, optionally with `modifier:value` pairs separated by spaces inside the brackets.

### Pattern modifiers

| Component | Modifier | Allowed values |
|---|---|---|
| `year` | `padding` | `zero` / `space` / `none` |
| | `repr` | `full` / `last_two` |
| | `sign` | `automatic` / `mandatory` |
| `month` | `padding` | `zero` / `space` / `none` |
| | `repr` | `numerical` / `long` / `short` (English only) |
| `day` | `padding` | `zero` / `space` / `none` |
| `week_number` | `padding` | `zero` / `space` / `none` |
| | `repr` | `ISO` (1..53) / `sunday` (0..53) / `monday` (0..53) |
| `weekday` | `repr` | `long` / `short` (English) / `sunday` / `monday` (numeric) |
| | `one_indexed` | `true` / `false` |
| `hour` | `padding` | `zero` / `space` / `none` |
| | `repr` | `24` / `12` |
| `period` | `case` | `lower` / `upper` |
| `minute` | `padding` | `zero` / `space` / `none` |
| `second` | `padding` | `zero` / `space` / `none` |

- **Example (defaults + a few patterns):** [`01-construct-and-display.typ`](./examples/08-datetime/01-construct-and-display.typ)
- **Example (full token cheatsheet):** [`04-format-tokens.typ`](./examples/08-datetime/04-format-tokens.typ)

---

## Field access methods

| Method | Returns | Notes |
|---|---|---|
| `.year()` / `.month()` / `.day()` | `int` or `none` | `none` for time-only values. |
| `.weekday()` | `int` or `none` | 1 = Monday … 7 = Sunday. `none` for time-only. |
| `.ordinal()` | `int` or `none` | Day of year (1..366). `none` for time-only. |
| `.hour()` / `.minute()` / `.second()` | `int` or `none` | `none` for date-only. |

---

## Arithmetic with `duration`

`duration(weeks:, days:, hours:, minutes:, seconds:)` builds a duration value. Then:

| Operation | Result |
|---|---|
| `dt2 - dt1` | `duration` |
| `dt + dur` | `datetime` (offset later) |
| `dt - dur` | `datetime` (offset earlier) |

A `duration` value exposes `.weeks()`, `.days()`, `.hours()`, `.minutes()`, `.seconds()` (each returns a float in those units).

- **Example:** [`03-arithmetic-with-duration.typ`](./examples/08-datetime/03-arithmetic-with-duration.typ)

---

## Pitfalls (agent-targeted)

1. **Mixing storage kinds in arithmetic is a type error.** Don't subtract a date-only from a time-only.
2. **Calling time-only methods on a date-only value returns `none`** (not an error). Guard before formatting if you depend on hours/minutes/seconds.
3. **Month / weekday names are English-only** in `repr: long` / `repr: short`. There is no localization yet; if you need other languages you must format the numeric form and translate yourself.
4. **`weekday()` is 1=Monday, 7=Sunday.** Many tools use 0=Sunday or 1=Sunday — don't carry that assumption over.
5. **`datetime.today()` is non-reproducible by default.** Use `SOURCE_DATE_EPOCH` or `--creation-timestamp` for builds where determinism matters.
6. **The `period` token only renders if `hour repr:12` is used.** Otherwise it's blank.

---

## Self-check

1. Did you supply the right subset of constructor args for the storage kind you actually want?
2. When formatting, are you using `[component modifier:value]` syntax (with spaces, not `=`)?
3. For builds requiring reproducibility, did you set `SOURCE_DATE_EPOCH` (or pass `--creation-timestamp`)?
4. When subtracting, did you confirm both operands are the same storage kind?
5. Does it compile? (`typst compile path.typ /tmp/out.pdf`)
