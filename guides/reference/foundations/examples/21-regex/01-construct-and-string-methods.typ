// 'regex("...")' creates a regex value. It can be used:
//   - as the separator / pattern arg to str methods: .split, .find, .match, .replace
//   - as a SHOW RULE selector to transform matched text in the document
//
// ESCAPING WARNING:
//   Both regex syntax and Typst strings use backslashes for escapes.
//   To produce a regex 'word boundary' (\b), you write '"\\b"' in a Typst
//   string -- the inner string is '\b', which the regex engine then sees.
//   To match a literal backslash, you write '"\\\\"' -> string '\\' -> regex '\'.
//
//   Cleaner alternative: use a RAW BLOCK and grab '.text':
//     regex(`\d+\.\d+\.\d+`.text)
//   This avoids double-escaping entirely.
//
// Regex syntax: Rust 'regex' crate (https://docs.rs/regex/latest/regex/#syntax).

split on , or ;:  #"a,b;c".split(regex("[,;]"))
all numbers:      #"build 142 v2.7 step 9".matches(regex("\d+")).map(m => m.text)
replace ints:     #"score: 100 / total: 250".replace(regex("\d+"), "??")
raw-block regex:  #"v1.2.3".matches(regex(`\d+\.\d+\.\d+`.text)).map(m => m.text)
