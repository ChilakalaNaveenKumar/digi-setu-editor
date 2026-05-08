// Demonstrates: inside a content block '[...]' you are back in MARKUP mode,
// so nested function calls there DO need the leading '#'.
// Inside a function's '(...)' arg list you are in CODE mode, so nested
// calls there do NOT need '#'.

#align(center + bottom)[
  #image("_assets/sample.png", width: 30%)

  *Caption sits below the centred image.*
]
