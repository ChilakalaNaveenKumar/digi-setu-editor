// Indexing model: strings are UTF-8. ALL lengths and indices are BYTE
// offsets, not codepoints and not characters. Negative indices wrap around
// to the end. Indexing into the middle of a multi-byte codepoint errors.
//
// Methods:
//   .len()                       byte length
//   .first(default:)             first grapheme cluster as a string
//   .last(default:)              last  grapheme cluster as a string
//   .at(index, default:)         cluster starting at this BYTE index
//   .slice(start, end, count:)   substring; pass either 'end' or 'count', not both
//   .clusters()                  array of grapheme clusters (handles emoji + combining marks)
//   .codepoints()                array of single Unicode codepoints
//   .rev()                       reversed string

#let s = "héllo"           // 'é' is 2 UTF-8 bytes -> len = 6
#let emoji = "👍🏼done"     // 'thumbs up: medium-light skin' = 1 cluster, multiple codepoints

len("héllo"):            #s.len()
first / last:            #s.first() / #s.last()
at(0) / at(-1):          #s.at(0) / #s.at(-1)
at(99, default: "?"):    #s.at(99, default: "?")

slice(1, 3):             #s.slice(1, 3)
slice(0, count: 3):      #s.slice(0, count: 3)
slice from -2:           #s.slice(-2)

// 's.slice(0, count: 2)' would ERROR: byte 2 lands in the middle of 'é'
// ("not a character boundary"). Slicing must align with codepoint boundaries.

clusters("👍🏼done"):     #emoji.clusters()
codepoints("👍🏼done"):   #emoji.codepoints()
rev("hello"):            #"hello".rev()
