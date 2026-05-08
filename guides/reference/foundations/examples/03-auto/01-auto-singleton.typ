// Demonstrates: 'auto' is a singleton value of its own type.
// It is NOT the same as 'none', NOT the same as 'false', and NOT the same
// as any zero/empty value. It signals "let the function pick a smart default
// based on context" (e.g. surrounding language, container size, etc.).

auto == auto:        #(auto == auto)
auto == none:        #(auto == none)
auto == false:       #(auto == false)
type(auto) is auto:  #(type(auto) == type(auto))
