// datetime arithmetic:
//   datetime - datetime  -> duration
//   datetime + duration  -> datetime
//   datetime - duration  -> datetime
// 'duration(...)' takes named args: weeks, days, hours, minutes, seconds.
// duration values support .hours(), .days(), etc. for unit conversion.

#let start = datetime(year: 2024, month: 1, day: 1)
#let end = datetime(year: 2024, month: 3, day: 1)

#let span = end - start
days between Jan 1 and Mar 1:    #span.days() \
hours between same:              #span.hours()

#let week = duration(days: 7)
one week after Jan 1: #(start + week).display() \
one week before Jan 1: #(start - week).display()
