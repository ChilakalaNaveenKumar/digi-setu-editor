// 'sys' is the system-interaction module. It currently exposes:
//
//   sys.version    -> version  (the Typst compiler that's compiling this file)
//   sys.inputs     -> dict     (CLI '--input key=value' flags)
//
// 'sys.inputs' values are ALWAYS strings. To get a number, bool, or
// structured value, parse manually with int(), float(), bool(), or one of
// the data-loading functions: json.decode, yaml.decode, toml.decode, etc.
//
// Quote the value on the CLI to include spaces:
//   typst compile --input title="My Doc" --input year=2026 file.typ

compiler version:        #sys.version
major / minor / patch:   #sys.version.major / #sys.version.minor / #sys.version.patch

is >= 0.13:              #(sys.version >= version(0, 13, 0))

// Defensive read: with no '--input' flags, sys.inputs is empty.
// '.at("k", default: ...)' avoids a missing-key error.
title input:             #sys.inputs.at("title", default: "(none provided)")
all CLI inputs:          #sys.inputs

// Polyfill template (NOT executed; tiling vs pattern was renamed in 0.13):
//   #let tiling = if sys.version >= version(0, 13, 0) { tiling } else { pattern }
