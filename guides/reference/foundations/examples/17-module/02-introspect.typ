// Module introspection:
//
//   "name" in some-module     -> bool. Test if a definition exists.
//                                Useful for safe / conditional access.
//   dictionary(some-module)   -> dict. Convert the module's contents to a
//                                dictionary so you can iterate keys/values.
//
// 'std' is the built-in standard module that contains every built-in
// definition, useful for capability checks.

#import "helpers.typ" as h

"add" in h:        #("add" in h)
"divide" in h:     #("divide" in h)
"table" in std:    #("table" in std)
"made-up" in std:  #("made-up" in std)

#let h-keys = dictionary(h).keys()
helpers exports: #h-keys

// Conditional access pattern.
#if "add" in h [
  fallback-free: #h.add(40, 2)
]
