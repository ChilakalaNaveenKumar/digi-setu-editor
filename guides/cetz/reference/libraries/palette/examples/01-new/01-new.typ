#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let p = cetz.palette.new(colors: (red, blue, green))
  for i in range(0, p("len")) {
    set-style(..p(i))
    circle((0, 0), radius: .5)
    set-origin((1.1, 0))
  }
})
