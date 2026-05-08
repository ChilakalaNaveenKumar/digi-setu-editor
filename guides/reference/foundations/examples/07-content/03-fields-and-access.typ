// A content value is composed of one or more elements, each with FIELDS.
// You can introspect the fields:
//   .fields()    -> dictionary of all fields explicitly present
//   .has("name") -> bool, true only if 'name' is explicitly present
//   .at("name", default: x) -> field value, with default fallback
//
// IMPORTANT: optional fields supplied by a 'set rule' do NOT appear in
// .fields(), .has(), or .at() -- only fields explicitly passed at the
// construction call site do.

#let r = rect(width: 6cm, height: 2cm, stroke: 0.5pt)

All explicit fields:    #r.fields()
has("width"):           #r.has("width")
has("inset"):           #r.has("inset")
at("width"):            #r.at("width")
at("inset", default: "<unset>"): #r.at("inset", default: "<unset>")

#r
