#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
#import circuiteria: util

== Plain padding

#util.lpad("0100", 8)   // 00000100

#util.lpad("11", 4)     // 0011

== Already long enough — no change

#util.lpad("12345", 3)  // 12345

== Used to make binary mux indices

#for i in range(4) [
  #i → #util.lpad(str(i, base: 2), 2) \
]
