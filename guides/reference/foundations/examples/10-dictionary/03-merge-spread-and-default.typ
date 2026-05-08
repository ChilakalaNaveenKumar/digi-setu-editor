// Merging:
//   d1 + d2                   last-wins on duplicate keys
//   d1 += d2                  in-place merge (last-wins)
//   (key: v, ..base)          mixed literal + spread (regular '()' is fine
//                             because the literal item disambiguates)
//   (:..a, ..b)               special form: ALL items are spreads. The ':'
//                             after '(' tells the parser this is a dict, not
//                             an array. WITHOUT the ':' you get the array
//                             error: "cannot spread dictionary into array".
//
// Removal & defaulting:
//   dict.remove("k")              returns the removed value, errors if absent
//   dict.remove("k", default: x)  returns x if absent, no error
//   dict.at("k", default: x)      same idea for read

#let defaults = (port: 8080, retries: 3, region: "us-east")
#let overrides = (port: 9090, region: "eu-west")

merge with +:                   #(defaults + overrides)
all-spread literal (':' form):  #(:..defaults, ..overrides)
mixed literal + spread:         #(env: "prod", ..defaults)

#let cfg = defaults + overrides
removed retries:     #cfg.remove("retries")
after removal:       #cfg
missing key default: #cfg.at("nope", default: "<unset>")
