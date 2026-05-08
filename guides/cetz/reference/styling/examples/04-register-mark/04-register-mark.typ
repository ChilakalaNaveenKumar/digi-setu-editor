#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  register-mark(":)", style => {
    circle((0, 0), radius: .5, fill: yellow)
    arc((0, 0),
        start: 180deg + 30deg,
        delta: 180deg - 60deg,
        anchor: "origin",
        radius: .3)
    circle((-0.15, 0.15), radius: .1, fill: white)
    circle((-0.10, 0.10), radius: .025, fill: black)
    circle(( 0.15, 0.15), radius: .1, fill: white)
    circle(( 0.20, 0.10), radius: .025, fill: black)
    anchor("tip",  ( 0.5, 0))
    anchor("base", (-0.5, 0))
  })
  line((0, 0), (3, 0), mark: (end: ":)"))
})
