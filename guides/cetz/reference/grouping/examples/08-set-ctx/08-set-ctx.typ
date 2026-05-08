#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  // Setting a custom transformation matrix (apply x-shear)
  set-ctx(ctx => {
    let mat = ((1, 0, .5, 0),
               (0, 1, 0,  0),
               (0, 0, 1,  0),
               (0, 0, 0,  1))
    ctx.transform = mat
    return ctx
  })
  circle((z: 0), fill: red)
  circle((z: 1), fill: blue)
  circle((z: 2), fill: green)
})
