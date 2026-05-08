# Foundations / 11 — `duration`

> **Typst version:** 0.14.2
> **Source page:** <https://typst.app/docs/reference/foundations/duration/>
> **Audience:** an LLM agent. Original prose; technical facts about the `duration` type. All examples below are verified to compile clean with `typst 0.14.2` (see `examples/11-duration/`).

---

## What it is

`duration` is a signed span of time. It can be positive or negative. Internally stored as a high-resolution count of seconds; the constructor's "weeks/days/hours/minutes/seconds" arguments are just convenient ways to specify it.

---

## Constructor

```
duration(
  weeks:   int = 0,
  days:    int = 0,
  hours:   int = 0,
  minutes: int = 0,
  seconds: int = 0,
) -> duration
```

All arguments are **named** and default to `0`. Components are summed: `duration(hours: 25)` is exactly the same value as `duration(days: 1, hours: 1)`.

Or: get a `duration` by subtracting two `datetime` values.

---

## Methods — the BIG gotcha

The methods do **NOT** return per-component values. They return the **total** duration expressed in that unit, as a `float`.

| Method | Returns | What you get |
|---|---|---|
| `d.weeks()` | `float` | total duration in weeks |
| `d.days()` | `float` | total duration in days |
| `d.hours()` | `float` | total duration in hours |
| `d.minutes()` | `float` | total duration in minutes |
| `d.seconds()` | `float` | total duration in seconds |

So `duration(days: 1, hours: 12).hours()` returns `36.0`, not `12.0`.

If you need per-component breakdowns (days = 1, hours = 12, minutes = 0, …), do the arithmetic yourself: e.g. `let h = calc.floor(d.hours()); let remaining = d - duration(hours: h); …`.

- **Example:** [`01-construct-and-totals.typ`](./examples/11-duration/01-construct-and-totals.typ)

---

## Arithmetic

| Operation | Result |
|---|---|
| `duration + duration` | `duration` |
| `duration - duration` | `duration` (can be negative) |
| `duration * int` / `int * duration` | `duration` (scaling) |
| `duration / duration` | `float` (ratio) |
| `datetime + duration` / `datetime - duration` | `datetime` |
| `datetime - datetime` | `duration` |
| `<`, `<=`, `==`, `!=`, `>=`, `>` between two durations | `bool` |

- **Example:** [`02-arithmetic.typ`](./examples/11-duration/02-arithmetic.typ)

---

## Pitfalls (agent-targeted)

1. **Method names look like component getters but return totals.** `(duration(days: 1, hours: 12)).hours() == 36.0`. Repeat after me: TOTAL.
2. **All constructor args must be `int`.** Floats and decimals are not accepted.
3. **`duration / duration` is a `float`,** which can be surprising — fits a calc-style operation, not a duration result.
4. **No native formatting.** `duration` has no `.display(...)`. If you want "1d 12h" output, build it yourself from the totals.

---

## Self-check

1. When you call `d.hours()`, are you intentionally asking for the TOTAL in hours, not the hours component?
2. Are all your constructor args integers?
3. If you need per-unit breakdown, did you write the floor/subtract loop yourself?
4. Does it compile? (`typst compile path.typ /tmp/out.pdf`)
