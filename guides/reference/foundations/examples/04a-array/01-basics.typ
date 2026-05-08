#set page(width: 14cm, height: auto, margin: 1cm)

== Construction and the trailing-comma gotcha

#(1, 2, 3) \
#()                // empty
#(42,)             // ONE element — note the trailing comma
#((1 + 2) * 3)     // NOT an array; just parens around arithmetic = 9

== Indexing (positive, negative, default)

#let xs = (1, 7, 4, -3, 2)

xs.first(): #xs.first() \
xs.last():  #xs.last() \
xs.at(2):   #xs.at(2) \
xs.at(-1):  #xs.at(-1) \
out-of-range with default: #xs.at(99, default: -1)

== Membership and search

#(3 in xs) \
#xs.find(calc.even) \
#xs.position(x => x < 0)

== Adding / removing in place

#let stack = (1, 2)
#stack.push(3)
#stack.push(4)
#let popped = stack.pop()
After push/pop: #stack (popped #popped)

#stack.insert(0, 99)
#stack.remove(1)
After insert at 0 and remove at 1: #stack
