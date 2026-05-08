// Supported arithmetic:
//   duration + duration                  -> duration
//   duration - duration                  -> duration  (can be negative)
//   duration * int / int * duration      -> duration  (scaling)
//   duration / duration                  -> float     (ratio)
//   datetime + duration / datetime - duration -> datetime
//   datetime - datetime                  -> duration
// Comparisons (<, ==, >, etc.) work between two durations.

#let day = duration(days: 1)
#let week = duration(weeks: 1)

`day + week`:   #(day + week).days()
`week - day`:   #(week - day).days()
`day * 3`:      #(day * 3).days()
`week / day`:   #(week / day)
`week > day`:   #(week > day)

#let start = datetime(year: 2024, month: 1, day: 1)
#let later = start + duration(days: 30)
30 days after Jan 1: #later.display()
