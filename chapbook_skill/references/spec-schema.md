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
| `kid_friendly` | bool | the one difficulty setting; turns on the kid rubric items (Riddle review) |

## `how_to_play`

`intro` (str), `mechanic` (str, the tinted rule box), `steps` (list[str], numbered), `checklist_title`
(str), `checklist` (list[str], one per stop: `"Stop 1 — <riddle name>"`), `notes` (list[str]).
Keep `notes` to 7 items or fewer; the page auto-shrinks type to fit and the build stops if it
cannot. The page also prints a generated **Before you go** box (from the stops' `access` records,
below) between the checklist and the notes; it is not written in the spec.

No hand-written How to Play string (intro, mechanic, steps, checklist, notes) may mention tickets,
admission, booking, opening hours, closing, prices or "free". The build scans for them, the way the
spoiler scan works, and stops on a hit: access facts come only from the records. Walking distance
and time are fine ("an hour on foot"); the map page prints them anyway.

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
| `units` | str | `"imperial"` (feet and miles): the only supported value, and the default. Any other value stops the build |
| `landmarks` | `"auto"` or list | optional, default `"auto"`: the engine picks a named landmark near every circle. A list pins them by hand (see below) |
| `landmark_exclude` | list[str] | optional. Names never to use as automatic landmarks |
| `cafe_break` | bool | optional, default false. Set true when the interview ticked Café stop |
| `street_labels` | list[str] | optional. Street names to print, exact OSM names. `[]` prints none (the usual choice); omitted prints any that fit |
| `frame` | dict | optional `{"bbox": [min_lon, min_lat, max_lon, max_lat]}` to lock the framing. Forces one page; every circle must fall inside it. Omit it: the engine frames and plans pages itself |
| `data` | dict | `{"manifest": "data/manifest.json"}`, relative to the spec file. Created by `scripts/fetch_osm.py` |
| `route` | dict | `mode` (`"foot"`), `avoid_steps` (bool, default true), `no_backtracking` (bool: a routing preference, not a claim), optional `claimed_distance_ft` |
| `representation_note` | str | printed under the legend; say what the map is and is not |
| `route_note`, `mechanic_note` | str | captions, on the first and last map page. Placeholders: `{stops}`, `{distance_mi}`, `{distance_ft}`, `{minutes}`. Hard-coded numbers raise a warning |
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
| `area_radius_ft` | float | optional circle radius, sized to the search. Default 130 ft, floor 100 ft |

What the generator does with these:

- **Route.** Solves each leg on the main connected OSM walking network (no private ways, no
  `foot=no`, steps excluded unless allowed; isolated fragments such as a path mapped inside a building
  are never used). With `no_backtracking`, later legs avoid streets already walked. Walking in and out
  of a stop down the same dead end, within its circle, is a visit, not a retrace. Measures total length
  and retracing, lists every major-road crossing, and flags legs that pass through another circle.
- **Retracing.** More than about 80 ft (25 m) of retracing warns and names the legs; it never blocks. The book
  makes no promise about backtracking either way.
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
- **Start (automatic).** The corner of two named streets within 500 ft of circle 1's edge, outside every
  circle (by about 100 ft), inside the route's padded extent and clear of every stop's secret terms; corners of
  two main streets first, then the nearest. Drawn as a hollow S disc with the label "Start", a legend entry
  and the caption "Start: A and B" on the first map page; never a leg. The report records it under
  `start`. No corner found is an error; a corner that moves after circles grow is a warning that the
  cold-solver packet must be printed again. There is no finish: the last stop ends the walk.
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
  500 ft, claimed distance more than 15% off, a café break with no room for any café label, a stop name or landmark label with no clear position,
  legend or caption overflow.
- **Warnings** (printed as `!! map warning`, recorded): each grown circle, unmarked or unknown
  crossing data, retracing over about 80 ft (names the legs), legs passing through other circles, hard-coded numbers in notes,
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

List of `{"riddle": {...}, "answer": {...}}`, one per stop, in walking order, plus an `access`
record on every ticketed or hours-limited stop (Access, below).

`riddle`: `name` (str, no answer in it), `stanzas` (**list of list[str]** — three stanzas, each a list of
its own centred lines, so you control every line break), `hint` (str; printed on the sealed hints
page after the last riddle, never on the riddle page itself), `ornament` (str, kind below),
and four data fields that are checked but not printed:

| Field | Required | Notes |
| --- | --- | --- |
| `evidence` | yes, 2+ | `{"text": str, "where": "public" \| "interior"}`; `interior` only where the map stop's `access` is `ticketed` or `hours_limited` and the stop's access `entry` is `required` |
| `action` | yes | the one thing the reader does to finish the stop; it must produce what the answer page names |
| `decoy` | yes | `{"name", "where", "why_wrong"}`; inside the circle or on the route, no ticket |
| `review` | yes | the rubric, below |

The hint is scanned for locating phrases (street corner, side of a square, address or house number,
"across from", "next to", numbered street, blocks or minutes from a place) and the build stops on a
hit; stanzas get a warning. The circle is the only locator (craft.md, hint rule).

### Riddle review

`review` records the rubric, one entry per item, as `"pass"` or `{"result": "pass"|"fail",
"note": str}` (a fail needs a note). A fail blocks the build unless `review.override` gives a
reason, which prints and is recorded. Items:

| Item | Passes when |
| --- | --- |
| `hint_recognition_only` | the hint adds recognition and does not locate |
| `evidence_observable` | every evidence item can be seen at the stop's access level and hours |
| `decoy_reachable` | the decoy is inside the circle or on the route, with no ticket or opening hour |
| `action_matches_answer` | doing the action produces the thing the answer page names |
| `no_shared_evidence` | no evidence item would also fit another stop's answer |
| `kid_countable` (kid-friendly only) | evidence is countable or pointable from a child's height |
| `kid_plain_words` (kid-friendly only) | architectural and historical terms are glossed in the same line |
| `kid_hint_names_decoy` (kid-friendly only) | the hint names the decoy outright |
| `kid_single_action` (kid-friendly only) | the instruction stanza is one concrete action |

Top-level `kid_friendly: True` turns on the four kid items (interview question 4). Use the note to
say what is verified and what is inferred ("lopsided canopy inferred from 'a quarter saved', not
seen").

**Cold solver.** `cold_solver.json` beside the spec, written by a reader who saw only the packet
printed by `scripts/riddle_pages.py <spec.py> --skeleton` (the skeleton carries a hash of the
riddle pages, so the report goes stale when they change): `{"riddles_sha256", "reader", "date",
"results": {"1": {"named", "basis": "hint"|"evidence"|"none", "line"}, ...}}`. A stop named from
its hint alone blocks; named from evidence passes and is recorded as easy. A missing or stale
report blocks unless top-level `riddles: {"skip_cold_solver": "<reason>"}` is set; the reason is
recorded as an unperformed check.

### Access

The map stop's `access` gives the kind: `open_air`, `ticketed` or `hours_limited`. An open-air
stop needs nothing more and must not carry a record. A ticketed or hours-limited stop carries an
`access` record on its book stop:

| Field | Required | Notes |
| --- | --- | --- |
| `entry` | yes | `required` (the riddle is solved inside) or `optional` (solved from outside; going in is extra) |
| `summary` | yes | one line, 110 characters or fewer: the hours or price as the official page gives them on the day you read it. Never the stop's name or a secret term |
| `fallback` | yes | what the walker does if it is shut. Never the stop's name or a secret term |
| `source` | yes | id of a `sources` record for the venue's own official page. Its `url` is printed and live-checked; its `accessed` date is printed as the checked date |

The build stops on: a gated stop without a record or with a missing field; an unknown `entry`;
extra fields (the URL and date belong in the source record); a summary over the limit; `optional`
entry with any `interior` evidence; a required-entry stop followed by any other stop (required
entry goes last); a record on an open-air stop; a box line containing a secret term. A `required`
stop whose evidence is all public warns (consider `optional`). A source `accessed` more than 30
days before the build warns: re-read the page and update the summary and date.

The summary and fallback are claims like any other: they enter the ledger cited to the access
source, so the source must say what the summary says.

From the records the engine prints:

- **Before you go box** (How to Play page): how many stops are open-air, then each gated stop by
  number, with its kind, entry, summary, checked date and fallback, and a pointer to the last page.
  Stops are never named; the cold-solver packet includes the box, so the reader checks it too.
- **Access-links page** (inside the back cover, after the credits): headed "This page names the
  stops", one entry per gated stop with its answer name, summary, fallback, checked date and the
  official URL. Printed only when some stop is gated.

`answer`: `name` (str), `subtitle_lines` (list[str], 2–4), `image` (filename inside `img/`; its
record in `images` supplies the printed credit), `paras` (2 claim items), `blocks` (2 claim tuples),
`notice` (one claim tuple, rendered in the tinted well), optional `timing_override` (str; see
Information timing).

A **claim item** is `{"text": str, "sources": [source_id, ...]}`; a **claim tuple** is
`(heading, text, [source_id, ...])`. Every answer-page item must carry at least one source id, and
the build stops if one does not. Front-matter prose (`maker.paras`, `acts.items[].text`,
`maker.facts`) may be written the same way when it states a fact; plain strings are allowed there
and are recorded as unsourced in the ledger. Schema v2 answer fields `credit` and plain-string
`paras`/`blocks` are retired and block the build.

The answer page measures itself and shrinks image and type until it fits; it prints
`!! answer N overflow` if it cannot. If you see that, cut text rather than editing the engine.

## Information timing

Every page is read at one moment: pre-walk (cover, How to Play with the Before you go box, map,
acts, maker), on site (riddle pages, hints page), post-hunt (spoiler divider, answer pages, the
treasure, credits) or any time (the sealed access-links page). The build scans post-hunt text, the
answer paragraphs, blocks and notice and the closing paragraphs and pull quote, and stops on a
sentence that asks for something at the stop: one that opens with an instruction ("Look up",
"Stand across the street", "Before you look up, look down") or points at the spot ("standing here",
"in front of you", "before you leave"). A sentence written for a return visit ("Next time you
pass, count the lamps") passes. `timing_override: "<reason>"` on an answer or on `closing` lets its
flagged sentences through as warnings in the build record.

## `spoiler`, `closing`, `credits`

- `spoiler`: `title_lines`, `lede`, `check_title`, `checks` (list[str]).
- `closing`: `kicker`, `title_lines`, `paras` (list[str], 2), `notes_title`, `note_fields`
  (list[str], each a prompt ending in a colon), `pullquote`.
- `credits`: `title_lines`, `intro`, `colophon`. Nothing else: the photograph and written-source
  lists are generated from the `images` and `sources` records below. A hand-written
  `credits.images` or `credits.sources` blocks the build. The page flows onto a "Continued" page
  when the records need one.

Long URLs are hard-broken across lines automatically.

## Provenance: `sources` and `images` (schema v3)

Two top-level record lists. Write them before the prose (SKILL.md step 3), run
`scripts/verify_provenance.py` after any change to them, and let the engine print the credits.

`sources`: list of records, one per thing read.

| Field | Required | Notes |
| --- | --- | --- |
| `id` | yes | `[a-z0-9_]+`, cited from claim items |
| `url` | yes | full `https://` URL of the page actually read |
| `title`, `publisher` | yes | printed; the publisher is dropped from the line when the title already contains it |
| `accessed` | yes | `YYYY-MM-DD` the page was read |
| `supports` | yes | what was read there that the book relies on — the specific facts, not "background" |
| `verified` | yes, `True` | you read the page yourself; `False` blocks unless `override` gives a reason |
| `weaker_claim` | optional | where this source and others disagree, or support less than the popular story, and what the book therefore says. Printed as "Note:" in the credits and as a build warning |
| `override` | optional | reason string that lets a failed live check (URL unreachable) pass; printed and recorded |

`images`: list of records, one per photograph used.

| Field | Required | Notes |
| --- | --- | --- |
| `id`, `file` | yes | `file` is the filename inside `img/`, matched to `answer.image` |
| `page_url` | yes | the Commons file page (`commons.wikimedia.org/wiki/File:...`) |
| `file_url` | optional | the original upload URL; checked against Commons when given |
| `author`, `licence` | yes | as the file page states them; `licence` must be in `ALLOWED_LICENCES` in `scripts/provenance.py` (CC0, public domain, CC BY, CC BY-SA 2.0–4.0). No NC or ND |
| `licence_url` | optional | defaults from the licence name |
| `caption` | optional | printed in the credits in place of the answer name; say what the photograph shows, honestly |
| `attribution` | optional | wording the licence or author requires, printed verbatim |
| `modified` | required if the file is not the Commons original | e.g. a Commons-served 960 px rendition; printed under the photo and in the credits, as CC BY asks |
| `checked` | yes | `YYYY-MM-DD` you opened the file page |
| `verified` | yes, `True` | author and licence confirmed on the file page by you |
| `override` | optional | reason that lets a failed live check pass; printed and recorded |

Optional `provenance: {"skip_live_checks": "<reason>"}` at top level lets a build run without
`provenance_check.json`; the reason is recorded as an unperformed check.

The build writes `<out>_record.json` beside the PDF: the records, the claim-to-source ledger, the
live-check results, warnings, overrides and unperformed checks. A source no claim cites, a claim
with no source, an image with no record and a stale check file all stop the build before drawing.

## Motif and ornament kinds

`cover_motif` accepts `fountain` or `crescent`; anything else draws the plain ringed diamond, which is
a perfectly good neutral cover.

`riddle.ornament` accepts `water`, `column`, `circle`, `obelisk`, `star`, `crescent`, `keystone`,
`square`, `grid`, and `arch`. An unknown kind falls back to `arch`. Pick the one that suggests the
stop's geometry without naming the place. Add a new kind to `riddle_ornament` in `scripts/engine.py`
only when no existing shape fits.
