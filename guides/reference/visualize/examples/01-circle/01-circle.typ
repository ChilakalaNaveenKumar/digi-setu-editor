#set page(width: 14cm, height: auto, margin: 8pt)

== `radius` vs `width`

#circle(radius: 18pt, fill: aqua)
#h(8pt)
#circle(width: 30%, stroke: 1pt + maroon)

== Wrapping content

#circle(fill: yellow.lighten(60%))[
  #set align(center + horizon)
  Auto sized
]

== Outline only

#circle(radius: 14pt, stroke: 2pt + red)
#h(8pt)
#circle(radius: 14pt, fill: red, stroke: 2pt + black)

== Custom inset

#circle(inset: 2pt, fill: green.lighten(70%))[Tight]
#h(8pt)
#circle(inset: 14pt, fill: green.lighten(70%))[Roomy]
