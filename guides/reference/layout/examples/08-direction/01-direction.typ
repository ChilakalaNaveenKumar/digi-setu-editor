// 'direction' is a TYPE describing one of the four cardinal flow
// directions. Used in 'stack(dir: ...)', 'text(dir: ...)', and
// 'page(direction: ...)'.
//
// Values:
//   ltr   left-to-right
//   rtl   right-to-left
//   ttb   top-to-bottom
//   btt   bottom-to-top

= Stack with each direction

#stack(dir: ltr, spacing: 4pt)[A][B][C][D]
#linebreak()
#stack(dir: rtl, spacing: 4pt)[A][B][C][D]
#linebreak()
#stack(dir: ttb, spacing: 4pt)[A][B][C][D]
#linebreak()
#stack(dir: btt, spacing: 4pt)[A][B][C][D]

= Methods on a direction

ltr.axis():  #ltr.axis()       (-> "horizontal") \
ttb.axis():  #ttb.axis()       (-> "vertical") \
ltr.sign():  #ltr.sign()       (-> 1) \
rtl.sign():  #rtl.sign()       (-> -1) \
ltr.start(): #ltr.start()      (-> left) \
ltr.end():   #ltr.end()        (-> right) \
ltr.inv():   #ltr.inv()        (-> rtl)

= 'direction.from(side)' / 'direction.to(side)'

#direction.from(left)   (-> ltr) \
#direction.from(right)  (-> rtl) \
#direction.to(top)      (-> btt) \
#direction.to(bottom)   (-> ttb)
