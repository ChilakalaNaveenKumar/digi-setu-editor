// '"name" in std' tests whether a definition exists in the standard library.
// Used together with 'sys.version' it is the foundation for POLYFILLS that
// keep one source file working across Typst versions.
//
// The classic example is the rename from 'pattern' to 'tiling' in 0.13: pick
// 'tiling' if available, fall back to 'pattern' otherwise. The argument
// shapes match, so callers don't have to care.
//
// Note: this file is just a runnable demonstration of the technique. The
// concrete 'pattern' / 'tiling' polyfill needs the visualize module's APIs
// in scope and is shown below as a comment, not executed.

// 1. Capability check.
"table" in std:    #("table" in std)
"made-up" in std:  #("made-up" in std)

// 2. Version-aware alias (this branch always runs because 'lorem' exists).
#let safe-lorem = if "lorem" in std { lorem } else { (n) => [Placeholder.] }

#safe-lorem(12)

// 3. Polyfill template (NOT executed):
//
//   #let tiling = if "tiling" in std { tiling } else { pattern }
//   #set page(fill: tiling(...))
//
// 'sys.version' lets you also branch on the version directly:
//
//   #if sys.version >= version(0, 13, 0) [ ... ] else [ ... ]
