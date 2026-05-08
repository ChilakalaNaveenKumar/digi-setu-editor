#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  register-coordinate-resolver((ctx, c) => {
    if type(c) == dictionary and "log" in c {
      c = c.log.map(n => calc.log(n, base: 10))
    }
    return c
  })
  circle((log: (10, 1e-6)),    radius: .25)
  circle((log: (100, 1e-6)),   radius: .25)
  circle((log: (1000, 1e-6)),  radius: .25)
})
