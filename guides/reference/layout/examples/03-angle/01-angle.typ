// 'angle' is a TYPE for rotation magnitudes.
// Units: 'deg' (degrees) and 'rad' (radians).
//   180deg == calc.pi rad

= Literal angles

#rotate(10deg)[Tilted slightly]
#rotate(0.524rad)[About 30 degrees]    // pi/6 ≈ 0.524

= Conversion methods

#(180deg).rad()                  // -> 3.14159...
#(1rad).deg()                    // -> 57.2957...

= Arithmetic

#(45deg + 30deg)                 // -> 75deg
#(2 * 45deg)                     // -> 90deg
#(180deg / 3)                    // -> 60deg

= Used as input to layout functions

#stack(
  dir: ltr,
  spacing: 1fr,
  ..range(8).map(i => box(rotate(45deg * i)[X])),
)
