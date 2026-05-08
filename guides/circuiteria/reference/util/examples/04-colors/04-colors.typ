#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
#import circuiteria: util

== Palette swatches as filled blocks

#circuiteria.circuit({
  import circuiteria: *
  let names = ("orange", "yellow", "green", "pink", "purple", "blue")
  let palette = (
    util.colors.orange,
    util.colors.yellow,
    util.colors.green,
    util.colors.pink,
    util.colors.purple,
    util.colors.blue,
  )
  for i in range(names.len()) {
    element.block(
      x: i * 1.5, y: 0, w: 1.2, h: 1.2,
      id: "sw" + str(i),
      name: names.at(i),
      fill: palette.at(i),
    )
  }
})
