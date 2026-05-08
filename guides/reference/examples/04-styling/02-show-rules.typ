#set page(width: 14cm, height: auto, margin: 1cm)

== Show-set rules compose

#show heading: set align(center)
#show heading: set text(font: "DejaVu Sans Mono", weight: "bold")

= Centered, monospaced

== Transformational show rule

#show heading.where(level: 2): it => block[
  ~ #emph(it.body) ~
]

== Italic and tilde-wrapped

== String and content show rules

#show "Project": smallcaps
#show "badly": "great"

We started Project in 2019.
The Project is progressing badly.

== Regex selector

#show regex("[A-Z]{3,}"): set text(red)

NASA, FBI, IBM, but lowercase stays the same.

== Where-selector with `.or`

#show heading.where(level: 1).or(heading.where(level: 2)): set text(navy)

= Navy
== Also navy
=== Default color
