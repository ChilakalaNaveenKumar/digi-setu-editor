// Demonstrates: primitive literals and numeric forms.
//   none      absence of a value
//   auto      smart default sentinel
//   true/false  booleans
//   ints     decimal (10), hex (0xFF), octal (0o77), binary (0b1011)
//   floats   3.14, 1e5, 2.5e-3

#let nothing = none
#let smart = auto
#let ok = true
#let dec = 42
#let hex = 0xFF
#let oct = 0o77
#let bin = 0b1011
#let pi-ish = 3.14
#let big = 1e5
#let tiny = 2.5e-3

Decimal: #dec, Hex: #hex, Octal: #oct, Binary: #bin.
Float: #pi-ish, Scientific: #big, Tiny: #tiny.
None? #(nothing == none). Smart default? #(smart == auto).
