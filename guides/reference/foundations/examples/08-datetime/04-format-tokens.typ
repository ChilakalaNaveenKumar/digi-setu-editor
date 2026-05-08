// Reference of useful display() pattern modifiers.
//
//   year     padding: zero|space|none   repr: full|last_two   sign: automatic|mandatory
//   month    padding: zero|space|none   repr: numerical|long|short
//   day      padding: zero|space|none
//   weekday  repr: long|short|sunday|monday   one_indexed: true|false
//   hour     padding: zero|space|none   repr: 24|12
//   period   case: lower|upper
//   minute   padding: zero|space|none
//   second   padding: zero|space|none

#let dt = datetime(year: 2024, month: 3, day: 5, hour: 9, minute: 7, second: 42)

ISO-style:        #dt.display("[year]-[month]-[day]") \
US-style long:    #dt.display("[month repr:long] [day], [year]") \
Short month:      #dt.display("[day padding:none] [month repr:short] [year]") \
Weekday long:     #dt.display("[weekday repr:long], [day] [month repr:long]") \
24h time:         #dt.display("[hour]:[minute]:[second]") \
12h with PM:      #dt.display("[hour repr:12]:[minute][period case:upper]") \
No-padding hour:  #dt.display("[hour padding:none]:[minute padding:zero]")
