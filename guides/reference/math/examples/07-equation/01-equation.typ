// 'math.equation' is the element produced by '$ ... $'. Most styling is
// done via 'set math.equation(...)' (or with show rules).
//
// Most-used fields:
//   block          bool                       inline (default) vs block
//   numbering      none|str|fn(int)->content  numbering pattern (block only)
//   number-align   alignment                  default end + horizon
//   supplement     none|auto|content|fn       'Equation' substitute for refs
//   alt            none|str                   accessibility text for AT
//   body           content                    the math content

#set math.equation(numbering: "(1)")
#set page(numbering: "1")

= Numbering and references

We define:
$ phi.alt := (1 + sqrt(5)) / 2 $ <ratio>

With @ratio, we get:
$ F_n = floor(1 / sqrt(5) phi.alt^n) $

= Number alignment (bottom)

#set math.equation(number-align: bottom)

We can calculate:
$ E &= sqrt(m_0^2 + p^2) \
    &approx 125 "GeV" $

#set math.equation(number-align: end + horizon)

= Reference supplement override

#set math.equation(numbering: "(1)", supplement: [Eq.])

We define:
$ E = m c^2 $ <energy>

With @energy, we have rest-energy.
