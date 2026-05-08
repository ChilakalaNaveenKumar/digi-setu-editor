// Supported arithmetic on decimal:
//   decimal +-*/ decimal      OK
//   decimal +-*/ int          OK (int is promoted to decimal)
//   decimal +-*/ float        ERROR -- intentional, to prevent silent precision loss
//
// To opt into imprecise arithmetic on a decimal, cast it explicitly:
//   float(decimal("3.14")) * 0.1     -- now in float-land

#let price = decimal("19.99")
#let tax-rate = decimal("0.08")

subtotal:    #price \
tax:         #(price * tax-rate) \
total:       #(price + price * tax-rate) \
3x price:    #(price * 3)
