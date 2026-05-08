// Each component is also accessible as a method that returns int (or none
// when the underlying datetime doesn't carry that component).
//
// 'datetime.today()' returns the current LOCAL date (with offset: auto).
// In CI/reproducible builds, set SOURCE_DATE_EPOCH or pass --creation-timestamp.
// In offset: int form, the int is hours offset from UTC.

#let date = datetime(year: 2024, month: 7, day: 15)

year:    #date.year()
month:   #date.month()
day:     #date.day()
weekday: #date.weekday()    // 1 = Monday, 7 = Sunday
ordinal: #date.ordinal()    // day-of-year (1..366)
hour on date-only:    #repr(date.hour())  // none

today (auto offset): #datetime.today().display()
today (UTC):         #datetime.today(offset: 0).display()
