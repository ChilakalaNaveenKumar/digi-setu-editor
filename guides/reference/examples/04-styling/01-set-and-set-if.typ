#set page(width: 14cm, height: auto, margin: 1cm)
#set heading(numbering: "I.")

= First section
= Second section

== Scoping a set rule with a content block

This list is affected: #[
  #set list(marker: [--])
  - Dash
  - Dash again
]

This list is not:
- Bullet
- Bullet again

== Conditional set rules with `set ... if`

#let task(body, critical: false) = {
  set text(red) if critical
  [- #body \ ]
}

#task(critical: true)[Food today?]
#task(critical: false)[Work deadline]
