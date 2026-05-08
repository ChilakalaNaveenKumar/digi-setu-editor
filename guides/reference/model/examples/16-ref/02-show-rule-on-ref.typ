// '#show ref: it => ...' lets you completely override how references render.
// The handler receives the ref element. Important fields:
//
//   it.target     label being referenced
//   it.element    the referenced element (or 'none' if not yet discovered)
//   it.supplement override (or 'auto' if unset)
//   it.form       "normal" | "page"
//
// 'it.element' may be 'none' even if the label exists -- Typst resolves
// references in stages, and an early pass may fire the show rule before the
// element is in scope. ALWAYS guard with 'if el == none { return it }'.

#set heading(numbering: "1.")
#set math.equation(numbering: "(1)")

#show ref: it => {
  let eq = math.equation
  let el = it.element
  // Skip everything except equation references.
  if el == none or el.func() != eq { return it }
  // Custom equation rendering: just the bracketed number, no "Equation" prefix.
  link(el.location(), numbering(
    el.numbering,
    ..counter(eq).at(el.location()),
  ))
}

= Beginnings <beginning>

In @beginning we prove @pythagoras.

$ a^2 + b^2 = c^2 $ <pythagoras>

Note how '@beginning' still renders as "Section 1" (default behavior),
while '@pythagoras' uses the custom show rule and renders as just '(1)'.
