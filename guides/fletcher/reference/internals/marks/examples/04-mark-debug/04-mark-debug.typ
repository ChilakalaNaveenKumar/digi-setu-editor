// Internals/marks 04 — mark-debug for a wide stealth arrow.

#import "@preview/fletcher:0.5.8" as fletcher
#set page(width: auto, height: auto, margin: 6pt)

#context {
  let mark = fletcher.MARKS.get().stealth + (angle: 45deg)
  fletcher.mark-debug(mark)
}
