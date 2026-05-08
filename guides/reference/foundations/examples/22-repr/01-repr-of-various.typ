// 'repr(value)' returns a string -- the debugger-style representation of
// 'value'. Inserting most values into content auto-uses repr already; the
// exceptions (which print THEIR OWN visible form, not their repr) are:
//   none, integers, floats, strings, content, and functions.
//
// repr is for DEBUGGING ONLY. It is NOT a stable serialization format and
// 'eval(repr(x))' is not guaranteed to recover x.

direct vs repr:
- none:      "#none"     vs   #repr(none)
- "hello":   "#"hello"" vs   #repr("hello")
- (1, 2):    #(1, 2)     vs   #repr((1, 2))
- [*Hi*]:    #[*Hi*]     vs   #repr([*Hi*])

length math (note imprecise repr):
- 2pt / 3 = #repr(2pt / 3)

unnamed function:
- x => x + 1 -> #repr(x => x + 1)

dictionary:
- (a: 1, b: 2) -> #repr((a: 1, b: 2))
