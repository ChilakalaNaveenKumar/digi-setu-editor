// 'version(...components) -> version'  (variadic ints OR a single array)
//
// Components beyond the explicitly given ones are an implicit infinite
// stream of zeros, so:
//   version()        == version(0)        == version(0, 0)        == ...
//   version(0, 8)    == version(0, 8, 0)  == version(0, 8, 0, 0)  == ...
//
// Named field access for the first three components:
//   v.major  v.minor  v.patch
// Beyond that, use .at(idx) (returns 0 if past the explicit length).
// .at also accepts negative indices (from the back of EXPLICIT components).

empty:                #version()
single component:     #version(1)
4 components:         #version(1, 2, 3, 4)
from array:           #version((1, 2, 3, 4))
mixed (flattened):    #version((1, 2), 3)

#let v = version(0, 14, 2)
v.major:              #v.major
v.minor:              #v.minor
v.patch:              #v.patch
v.at(0):              #v.at(0)
v.at(3) (implicit 0): #v.at(3)
v.at(-1):             #v.at(-1)

// Trailing zeros are equivalent.
0.8 == 0.8.0:         #(version(0, 8) == version(0, 8, 0))
empty == 0:           #(version() == version(0))
