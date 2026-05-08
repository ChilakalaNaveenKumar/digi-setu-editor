#set page(width: 14cm, height: auto, margin: 8pt)

== Endpoint vs length/angle

#line(length: 100%)
#line(end: (60%, 20pt))
#line(length: 4cm, angle: 30deg, stroke: 2pt + maroon)

== Stroke variants

#stack(
  spacing: 8pt,
  line(length: 100%, stroke: 2pt + red),
  line(length: 100%, stroke: (paint: blue, thickness: 4pt, cap: "round")),
  line(length: 100%, stroke: (paint: blue, thickness: 1pt, dash: "dashed")),
  line(length: 100%, stroke: (paint: blue, thickness: 1pt,
                              dash: ("dot", 2pt, 4pt, 2pt))),
)

== Vertical separator inline

Left #h(6pt)
#box(line(length: 1em, angle: 90deg, stroke: 0.5pt + gray))
#h(6pt) Right

== Signature line

Sign here: #h(0.5cm) #line(length: 6cm, stroke: 0.5pt)
