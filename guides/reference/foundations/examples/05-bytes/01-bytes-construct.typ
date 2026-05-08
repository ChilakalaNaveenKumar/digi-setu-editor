// 'bytes(value)' converts to the bytes type. Accepted inputs:
//   - str   -> UTF-8 encoded
//   - array of int (each 0..255) -> direct
//   - bytes -> identity
// .len() returns the count of bytes.

#let from-str = bytes("Hi!")
#let from-arr = bytes((72, 105, 33))

from-str length: #from-str.len()
from-arr length: #from-arr.len()
equal as bytes:  #(from-str == from-arr)
