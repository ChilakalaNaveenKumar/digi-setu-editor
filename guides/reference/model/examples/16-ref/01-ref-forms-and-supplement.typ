// 'ref(target, supplement: ?, form: "normal"|"page")' cross-references a label
// or cites a bibliography entry.
//
// Two forms:
//   "normal" (default): textual reference. Picks up the target's number and
//                       a localized supplement (e.g. "Section 1", "Figure 3").
//                       The target MUST be referenceable: heading / figure /
//                       equation / footnote (or a custom figure with kind:).
//   "page":             page-number reference. Target may be ANY label.
//
// Markup shorthand:
//   @label              same as #ref(<label>)
//   @label[Custom]      same as #ref(<label>, supplement: [Custom])
//
// 'supplement:' overrides the localized word ("Section", "Figure"...). It can
// be:
//   none / auto / content / function(element -> content)

#set page(numbering: "1")
#set heading(numbering: "1.")
#set math.equation(numbering: "(1)")

= Introduction <intro>
Recent work in typesetting has rekindled interest. @results

== Method <method>
We extend prior approaches.

= Results <results>
We discuss the approach in @method (see #ref(<results>, form: "page")).

== Performance <perf>
Equation @slow shows the worst-case bound.
$ T(n) = O(2^n) $ <slow>

#pagebreak()

Reference forms shown side by side:

- bare @intro            -> auto-supplement ("Section 1")
- @intro[Chapter]        -> custom supplement ("Chapter 1")
- #ref(<intro>)          -> identical to '@intro'
- #ref(<slow>)           -> Equation reference using built-in numbering
- #ref(<perf>, form: "page") -> jumps to the page where 'perf' lives
