#set page(width: 14cm, height: auto, margin: 1cm)

== Loading and templating

#let f = json("_assets/forecast.json")
*Forecast for #f.city:*

#table(
  columns: 3,
  [*Day*], [*Temp (°C)*], [*Weather*],
  ..for d in f.days {
    ([#d.name], [#d.temp], [#d.weather])
  },
)

== Encode round-trip

#let payload = (
  status: "ok",
  count: 3,
  items: ("a", "b", "c"),
  empty: none,
)
#let s = json.encode(payload, pretty: false)
Encoded: #raw(s) \
Round-trip equal: #(json(bytes(s)) == payload)
