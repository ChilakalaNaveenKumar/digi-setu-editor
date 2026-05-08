// .at(i)              -> int (the byte value at index i)
// .slice(start, end)  -> bytes (sub-range; end exclusive)
// .slice(start, count: n) -> alternative form using a count
// Convert back out:
//   str(b)    decodes UTF-8
//   array(b)  produces an int array of byte values

#let data = bytes("Hello, world!")
total bytes:        #data.len()
byte at 0 ('H'=72): #data.at(0)
slice(7, 12) as str:    #str(data.slice(7, 12))
slice(0, 5) as int arr: #array(data.slice(0, 5))
slice(0, count: 5):     #str(data.slice(0, count: 5))
