// Demonstrates: relative vs absolute path resolution.
// Relative path: resolved from the directory of the current Typst file.
// Absolute path (leading '/'): resolved from the PROJECT ROOT.
// Default project root = directory of the main file. Override with --root.
// Security: files outside the project root cannot be read.

= Relative path
#image("_assets/sample.png", width: 1cm)

= Absolute path (project root = this file's directory by default)
#image("/_assets/sample.png", width: 1cm)
