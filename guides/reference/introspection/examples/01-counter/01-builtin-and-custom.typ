#set page(width: 14cm, height: auto, margin: 1cm)
#set heading(numbering: "1.")

= Introduction
Body. Heading counter raw value: #context counter(heading).get()

= Background
Roman: #context counter(heading).display("I")

== Sub
Default: #context counter(heading).display() \
Custom:  #context counter(heading).display((..n) =>
  n.pos().map(str).join("·"))

= Custom theorem counter

#let thm = counter("theorem")
#let theorem(body) = block[
  #thm.step()
  *Theorem #context thm.display():* #body
]

#theorem[$1 = 1$]
#theorem[$2 < 3$]
#theorem[$forall epsilon > 0$ ...]

Final theorem count: #context thm.final().first()
