// 'scope:' is a dictionary of names made visible to the evaluated source.
// Without it, the source has access to globals only -- no caller-local
// bindings leak in.

scope = (x: 2): #eval("x + 1", scope: (x: 2))

// Scope values can be ANY type, including content captured with [...].
#let templated = eval(
  "name + colon + body",
  scope: (
    name: [Notice],
    colon: [: ],
    body: [the system has been updated.],
  ),
)
#templated
