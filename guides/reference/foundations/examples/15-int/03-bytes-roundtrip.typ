// int <-> bytes conversion.
//
// value.to-bytes(endian: "little"|"big", size: int) -> bytes
//   Default size is 8. If 'size' is smaller than what the int needs, bytes are
//   truncated from the high end (BE) or low end (LE). For negative ints, an
//   under-sized buffer can drop the sign bit -- round-tripping then yields a
//   different number.
//
// int.from-bytes(b, endian: "little"|"big", signed: bool) -> int
//   Length of 'b' must be <= 8. With 'signed: true' (default), the high bit
//   is treated as the sign bit. With 'signed: false', the result is always
//   non-negative.

#let n = 12345
#let le = n.to-bytes(size: 4, endian: "little")
#let be = n.to-bytes(size: 4, endian: "big")

n:               #n
LE bytes:        #array(le)
BE bytes:        #array(be)
roundtrip LE:    #int.from-bytes(le, endian: "little")
roundtrip BE:    #int.from-bytes(be, endian: "big")

// Sign behavior: a single byte 0xFF is -1 signed, 255 unsigned.
#let one-byte = bytes((255,))
0xff signed:     #int.from-bytes(one-byte)
0xff unsigned:   #int.from-bytes(one-byte, signed: false)
