// IEEE 754 byte-level conversion. Useful for binary file I/O.
//
//   x.to-bytes(endian: "little", size: 8) -> bytes
//     size MUST be 4 (binary32) or 8 (binary64); default 8.
//     endian "little" (default) or "big".
//   float.from-bytes(b, endian: "little") -> float
//     bytes MUST have length 4 or 8; format inferred from length.

// 1.0 in IEEE binary64: 0x3FF0000000000000
1.0 to-bytes (little, 8): #array((1.0).to-bytes())
1.0 to-bytes (big, 8):    #array((1.0).to-bytes(endian: "big"))
1.0 to-bytes (little, 4): #array((1.0).to-bytes(size: 4))

from-bytes (binary64 LE): #float.from-bytes(bytes((0, 0, 0, 0, 0, 0, 240, 63)))
from-bytes (binary64 BE): #float.from-bytes(bytes((63, 240, 0, 0, 0, 0, 0, 0)), endian: "big")
from-bytes (binary32 LE): #float.from-bytes(bytes((0, 0, 128, 63)))
