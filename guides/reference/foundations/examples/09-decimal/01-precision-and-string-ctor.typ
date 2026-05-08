// 'decimal' is fixed-point base-10 arithmetic. Use it whenever exact
// fractional values matter: currency, audited totals, exact percentages.
//
// CRITICAL: ALWAYS construct from a string literal: decimal("0.1").
//   - decimal("0.1") + decimal("0.2") == decimal("0.3")  EXACT.
//   - 0.1 + 0.2                       != 0.3              (float drift).
//
// decimal(<int>)         OK -- exact.
// decimal("<digits>")    OK -- recommended for fractions.
// decimal(<float>)       DISCOURAGED -- emits a warning; imprecise round-trip.

Decimal: #(decimal("0.1") + decimal("0.2")) \
Float:   #(0.1 + 0.2)
