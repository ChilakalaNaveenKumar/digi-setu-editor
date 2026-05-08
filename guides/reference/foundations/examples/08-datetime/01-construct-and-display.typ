// 'datetime(...)' takes named args. Which fields you pass decides storage:
//   year + month + day                                  -> date only
//   hour + minute + second                              -> time only
//   year + month + day + hour + minute + second         -> full datetime
// .display(pattern) renders to a string. Pattern is composed of components
// in [brackets], each with optional space-separated 'modifier:value' pairs.

#let date = datetime(year: 2024, month: 7, day: 15)
#let time = datetime(hour: 18, minute: 2, second: 23)

date default:                        #date.display() \
date custom (last_two year):         #date.display("y:[year repr:last_two]") \
date custom (long month name):       #date.display("[month repr:long] [day], [year]") \
time default:                        #time.display() \
time custom (12-hour with period):   #time.display("[hour repr:12]:[minute][period]")
