// Wherever a function expects content, you may pass:
//   - a content value (markup block, element call, [bracket] block)
//   - a string  (treated as plain text content)
//   - none      (treated as empty content)
// This means body parameters are flexible: the same call site accepts all
// three input forms.

#box(stroke: 0.5pt, inset: 5pt, [As a content value])
#box(stroke: 0.5pt, inset: 5pt, "As a plain string")
#box(stroke: 0.5pt, inset: 5pt, none)
