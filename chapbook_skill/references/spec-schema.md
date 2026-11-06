# Spec schema

`SPEC` is one Python dict. `templates/spec_example.py` is a complete instance of every book section —
copy it and replace the content rather than writing a spec from scratch. Its map is a placeholder
that stops the build; write the map from `templates/map_spec_example.py` and paste it in. Every key below is required unless marked
optional. Tuples are `(label, value)` pairs. The map has no drawing coordinates: it is described in
geographic terms and `scripts/mapgen.py` derives every position.

## Top level

| Key | Type | Notes |
| --- | --- | --- |
| `slug` | str | filename-safe id |
| `author` | str | PDF metadata |
| `display_font` | str | `"Cormorant"` or `"Garamond"` only. Not `"EBGaramond"`. |
| `palette` | dict | keys `paper`, `ink`, `accent`, `accent2`, `gold`, and optional `water`, all hex strings |
| `cover_motif` | str | motif kind, see below |
| `blank_label` | str | small caps line on any padding page |
| `cover_kicker` | str | e.g. `"Bath · A walking hunt"` |
| `title_line1`, `title_line2` | str | cover title, two lines |
| `subtitle` | str | one line, used in PDF metadata |
| `subtitle_lines` | list[str] | cover subtitle, wrapped by hand |
| `cover_tagline_lines` | list[str] | italic couplet under the subtitle |

## `how_to_play`

`intro` (str), `mechanic` (str, the tinted rule box), `steps` (list[str], numbered), `checklist_title`
(str), `checklist` (list[str], one per stop: `"Stop 1 — <riddle name>"`), `notes` (list[str]).
Keep `notes` to 7 items or fewer; the page auto-shrinks type to fit and prints
`!! how_to_play overflow` if it cannot.

## `map` (schema v2)

The map is generated from cached OpenStreetMap data and the interview inputs. Nothing on it is
positioned by hand. It is a "bearings" map: it helps the reader get their bearings between riddle
stops, not navigate turn by turn. The old v1 fields (`blocks`, `bands`, `streets`, `labels`,
`label_at`, `north_at`, box-fraction `at`) are retired and a v1 map stops the build.

| Key | Type | Notes |
| --- | --- | --- |
| `version` | int | `2` |
| `representation` | str | `"geographic"`, the only supported value |
| `style` | str | optional, `"bearings"`, the only supported value. The retired `"detailed"` style stops the build |
| `purpose` | str | `"orientation"` |
| `title` | str | page title; scanned for secret terms. Long titles shrink to fit the page |
| `units` | str | `"imperial"` (feet and miles) or `"metric"`, default `"metric"`. Use imperial for US readers |
| `landmarks` | `"auto"` or list | optional, default `"auto"`: the engine picks a named landmark near every circle. A list pins them by hand (see below) |
| `landmark_exclude` | list[str] | optional. Names never to use as automatic landmarks |
| `cafe_break` | bool | optional, default false. Set true when the interview ticked Café stop |
| `street_labels` | list[str] | optional. Street names to print, exact OSM names. `[]` prints none (the usual choice); omitted prints any that fit |
| `frame` | dict | optional `{"bbox": [min_lon, min_lat, max_lon, max_lat]}` to lock the framing. Forces one page; every circle must fall inside it. Omit it: the engine frames and plans pages itself |
| `data` | dict | `{"manifest": "data/manifest.json"}`, relative to the spec file. Created by `scripts/fetch_osm.py` |
| `route` | dict | `mode` (`"foot"`), `avoid_steps` (bool, default true), `no_backtracking` (bool), optional `claimed_distance_m` |
| `representation_note` | str | printed under the legend; say what the map is and is not |
| `route_note`, `mechanic_note` | str | captions, on the first and last map page. Placeholders: `{stops}`, `{distance_mi}`, `{distance_ft}`, `{distance_km}`, `{distance_m}`, `{minutes}`. Hard-coded numbers raise a warning |
| `padding` | float | optional, default `0.07`; extra extent around route and circles when there is no `frame` |
| `labels` | dict | optional `{"suppress": [str, ...]}`: extra names never to print |
| `stops` | list | one per stop, in walking order, same count as the book's `stops` |

A pinned `landmarks` list holds items of either kind:

- `{"osm": "way/<id>" or "relation/<id>", "label": "NAME|SECOND LINE"}`: a building, park or other
  mapped outline. Drawn as a quiet block; one more than 3× the largest circle's area draws as a faint
  dashed outline instead.
- `{"road": "<exact OSM name>", "label": "NAME"}`: a named road, drawn as a slightly stronger band and
  labelled like any other landmark, set level beside the road.

Each `map.stops` item:

| Key | Type | Notes |
| --- | --- | --- |
| `zone` | str | stop name shown on the circle, `\|` splits lines. In a live book use the riddle's name. Never the answer or another stop's answer |
| `target` | str | private: `node/<id>`, `way/<id>` or `relation/<id>` of the thing to be found. Never printed. Fetch a relation target's full geometry by listing its id to `fetch_osm.py` |
| `target_point` | dict | instead of `target`, when the thing is not in OSM: `{"lat", "lon", "source": <URL>, "verified": bool, "note"}`. Unverified points raise a warning |
| `view_from` | str | optional `way/<id>`: public street from which the target is seen, when you look rather than visit |
| `answer_name` | str | private: the answer as it appears on the answer page |
| `secret_terms` | list[str] | private: every word or name that would give the answer away, including the building or street that holds the target when that is itself the giveaway. Never a word used in a zone name |
| `access` | str | `open_air`, `ticketed` or `hours_limited`. Ticketed and hours-limited stops must come last |
| `order_waiver` | str | map tests only: reason a ticketed stop is not last. A full book refuses it |
| `shares_area_with` | int | optional: the previous stop's number, when two targets are steps apart and share one circle |
| `area_radius_ft` | float | optional circle radius, sized to the search. Default 130 ft, floor 100 ft. `area_radius_m` is accepted for metric specs |

What the generator does with these:

- **Route.** Solves each leg on the main connected OSM walking network (no private ways, no
  `foot=no`, steps excluded unless allowed; isolated fragments such as a path mapped inside a building
  are never used). With `no_backtracking`, later legs avoid streets already walked. Walking in and out
  of a stop down the same dead end, within its circle, is a visit, not a retrace. Measures total length
  and retracing, lists every major-road crossing, and flags legs that pass through another circle.
- **Circles.** Each contains its target but is centred 30–55% of the radius away from it, in a direction
  chosen to keep circles apart. The route is drawn outside circles only, so no line ends on a target.
  Inside each circle every street and path is drawn in full over a light shading. Overlapping circles
  stop the build.
- **Pages.** Before drawing, the planner chooses 1–3 map pages, splitting the walk between stops
  (never inside a shared circle). Every circle must read at its page's scale: its radius on paper at
  least the width of its number disc (more for a shared circle's row of discs), and 6 pt of paper between neighbouring circles. Plans that keep every circle at its
  interview size always win; among them, the fewest pages. Only when none exists may circles grow,
  up to 400 ft, scaled about their target so its off-centre position is unchanged; then the fewest
  pages and least growth win. A grown circle may not overlap another or take in another stop's
  target. Each later page starts with the previous page's last stop, drawn with its circle (at least a
  ring around its number disc), and says "The walk continues from stop N."
- **Landmarks (`"auto"`).** Every named feature in the data is ranked by kind (historic sites,
  places of worship, museums, civic buildings, towers and bridges first; then stations, parks,
  squares, schools; then other named buildings and main streets), a Wikidata or Wikipedia tag, size and
  distance. Names matching any secret term, and the targets themselves, are excluded. The engine then
  searches landmark choices and label positions together for a clean placement with at least one
  landmark within 500 ft of every circle's edge. Different inputs can give different landmarks; the
  same inputs and data always give the same map.
- **Café break (`cafe_break`).** Up to three real, named cafés, bakeries, ice-cream shops or
  restaurants within about 500 ft of the leg that starts nearest halfway, outside every circle. Each is
  marked with a cup symbol and its own name, the legend gains "Café break", and the page drawing that
  leg carries the caption "Café break after stop N: A, B or C. From OpenStreetMap; check opening hours
  before you go." It is never a numbered stop.
- **Base map.** Water, main streets, the streets the route uses, and the landmarks, clipped to the frame
  and lightly simplified. Everything else is left out. North is up.
- **Labels.** Fixed sizes: stop names 6.5 pt, features 6.2 pt, streets and cafés 6.0 pt; floor 6.0 pt,
  never shrunk. Stop names float onto their circle's rim, partly inside. A landmark label never sits
  across water from its landmark. Every label must be clear of other labels, number discs, route,
  circles, café symbols, scale bar, north arrow, attribution and the frame edge.
- **Scale bar and north arrow.** One group, side by side, placed before any labels, in the first
  corner (bottom-left, top-left, top-right, bottom-right) clear of circles, route, landmarks,
  attribution and streets, sliding at most 12 pt along the edge; if no corner is fully clear of
  streets, the one with the least overlap. The north arrow sits on the border side of the group. A
  multi-page map uses one bar value on every page when a bar of that value is 28–120 pt long on all of
  them; otherwise each page picks its own. A page whose scale differs from the previous page's by more
  than 10% prints "Zoomed out from page N" (or "Zoomed in") under its bar.
- **Blocking failures** (the build stops, no PDF): map placeholder not replaced, v1 schema, retired
  style, data not matching its manifest hash, unknown OSM ids or road names, unsolvable leg, secret
  term in title, notes or stop names, ticketed stop not last, circle below the 100 ft floor,
  overlapping circles, circle outside a locked frame, no legible page plan within 3 pages even with
  growth (one report lists every page and constraint with its fix), a circle with no landmark within
  500 ft, claimed distance more than 15% off, retracing despite `no_backtracking` (names the legs), a
  café break with no room for any café label, a stop name or landmark label with no clear position,
  legend or caption overflow.
- **Warnings** (printed as `!! map warning`, recorded): each grown circle, unmarked or unknown
  crossing data, retracing, legs passing through other circles, hard-coded numbers in notes,
  unverified target points, a stop name placed beside its circle because it could not float onto
  the rim, no fully clear corner for the scale group.

In a full book, every pre-divider string (cover, how to play, map, acts, maker, all riddles) is also
scanned against every stop's secret terms before rendering. A hit stops the build.

`scripts/build_map.py <map_spec.py> <out.pdf>` renders the map pages alone and writes
`<out>_record.json`: generator version, code and spec hashes, data manifest check, route and
crossings, page plan (stops, scale, grown circles per page), landmarks chosen with their
alternatives, café candidates with OSM links, labels placed / dropped / suppressed, automated checks
run and checks not performed. See `templates/map_spec_example.py`.

## `acts`

`kicker`, `title_lines` (list[str]), `lede`, `items` (list of `{"numeral", "name", "text"}`, use
exactly three), `closer`.

## `maker`

`kicker`, `title_lines`, `standfirst`, `paras` (list[str], 3 works well), `facts_title`,
`facts` (list of `(label, value)` tuples, 5–7), `pullquote`.

## `stops`

List of `{"riddle": {...}, "answer": {...}}`, one per stop, in walking order.

`riddle`: `name` (str, no answer in it), `stanzas` (**list of list[str]** — three stanzas, each a list of
its own centred lines, so you control every line break), `hint` (str), `ornament` (str, kind below).

`answer`: `name` (str), `subtitle_lines` (list[str], 2–4), `image` (filename inside `img/`),
`credit` (str, full author and licence), `paras` (list[str], 2 paragraphs), `blocks` (list of
`(heading, text)` tuples, 2 items), `notice` (a single `(heading, text)` tuple, rendered in the tinted
well).

The answer page measures itself and shrinks image and type until it fits; it prints
`!! answer N overflow` if it cannot. If you see that, cut text rather than editing the engine.

## `spoiler`, `closing`, `credits`

- `spoiler`: `title_lines`, `lede`, `check_title`, `checks` (list[str]).
- `closing`: `kicker`, `title_lines`, `paras` (list[str], 2), `notes_title`, `note_fields`
  (list[str], each a prompt ending in a colon), `pullquote`.
- `credits`: `title_lines`, `intro`, `images` (list[str], one line per photo with author, licence and
  full URL), `sources` (list[str], one per written source with full URL and what it supports),
  `colophon`.

Long URLs are hard-broken across lines automatically.

## Motif and ornament kinds

`cover_motif` accepts `fountain` or `crescent`; anything else draws the plain ringed diamond, which is
a perfectly good neutral cover.

`riddle.ornament` accepts `water`, `column`, `circle`, `obelisk`, `star`, `crescent`, `keystone`,
`square`, `grid`, and `arch`. An unknown kind falls back to `arch`. Pick the one that suggests the
stop's geometry without naming the place. Add a new kind to `riddle_ornament` in `scripts/engine.py`
only when no existing shape fits.
