// 'duration(weeks:, days:, hours:, minutes:, seconds:)' -- all named, all
// default to 0. Components are summed (so 25 hours == 1 day 1 hour stored).
//
// METHODS RETURN TOTALS, NOT COMPONENTS:
//   d.weeks()    -> total duration expressed in weeks  (float)
//   d.days()     -> total duration expressed in days   (float)
//   d.hours()    -> total duration expressed in hours  (float)
//   d.minutes()  -> total duration expressed in minutes (float)
//   d.seconds()  -> total duration expressed in seconds (float)
// So a 1-day-12-hour duration .hours() is 36.0, not 12.0.

#let span = duration(days: 1, hours: 12)

in seconds: #span.seconds()
in minutes: #span.minutes()
in hours:   #span.hours()
in days:    #span.days()
in weeks:   #span.weeks()
