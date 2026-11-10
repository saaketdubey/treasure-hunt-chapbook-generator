# Writing and design craft

## The one rule that cannot be broken

A riddle page must not reveal its own answer. Not in the riddle name, not in the stanzas, not in the
ornament, not in the map label, not in the hint. The map gives walking order and a broad zone only.
The reader's whole pleasure is the gap between "a room with no corners" and "the Circus".

Before rendering, reread every riddle page against the corresponding answer page and delete any proper
noun, dedication date, sculptor's name, or building name that gives it away. Street names in the
optional hint are acceptable; the answer's own name is not.

## Language and units

Every book is written in American English and uses imperial units (feet and miles). Both are
fixed for every book. Do not adapt spelling or units to the place or to the reader.

## Riddles

Three stanzas, each a list of centred lines of roughly equal length (under about 48 characters so
they do not wrap). Stanza one places the reader without naming the place. Stanza two gives the
observable evidence: what to count, what shape, what is carved. Stanza three gives the instruction:
what to do or find, phrased as an action, not as the name of the thing.

A riddle is written from evidence, so write the evidence first. Each riddle carries four data
fields beside its stanzas, and the stanzas are built from them:

- `evidence` — two or more observations a reader can make on the spot, each tagged `public`
  (visible from public ground at any hour) or `interior` (needs to be inside, allowed only where
  the map stop's `access` is `ticketed` or `hours_limited` and going in is `required`). If the
  riddle can be solved from outside, mark entry `optional` and keep every item public: a walker
  who arrives after closing still finishes the stop. Evidence is countable or pointable: a
  number of windows, a carved animal, a missing half of a canopy, a plaque at knee height. "Georgian
  proportions" is not evidence; "three storeys and a rusticated ground floor" is. Historical facts
  the reader cannot see belong on the answer page, not in the riddle.
- `action` — the one thing the reader does to finish the stop: photograph, count, read, touch,
  stand under. It must produce the same thing the answer page names, so a reader who did the
  action has found the answer and knows it.
- `decoy` — the handsome, famous or obvious thing nearby that is the wrong answer: `name`, `where`
  (relative to the circle or the route, so the reader meets it without a detour), `why_wrong`
  (which piece of evidence it fails). A decoy that needs a walk, a ticket or an opening hour is
  not a decoy, it is a second stop.
- `hint` — one or two sentences; see the hint rule below. Hints print together on one sealed
  hints page after the last riddle, so the riddle page carries no hint at all, only a pointer.
  Write each hint to stand alone: a walker may read the whole page by accident, and nothing in
  one hint should help with another stop.

Register: plain, present tense, second person. One inversion per riddle (the famous doorway that
is the wrong house, the grand room behind the plain wall); two make it a trick, none make it a
description. Use a tangible image per stanza and no adjectives of praise.

The hint rule, two tests. A hint may add recognition: the kind of thing to look for, what to count,
which nearby famous thing is the wrong answer. A hint may not locate: no street corner, side of a
square, address or house number, "across from X" or "next to Y", compass direction from a named
place, or anything else that narrows the position beyond the map circle. The circle is the only
locator in the book. Name the decoy in the hint ("the famous crescent two minutes north is not it"
fails the rule; "the famous crescent is the wrong answer" passes).

Kid-friendly (`kid_friendly: True`, from interview question 4) is the one difficulty setting, and it
changes four things: evidence is countable or pointable from a child's height (a carved dog at eye
level, not a frieze four storeys up); words are plain, with any architectural or historical term
glossed in the same line ("a keystone — the wedge at the top of the arch"); the hint names the
decoy outright; the instruction stanza is one concrete action. Unset, riddles are written to one
adult standard.

Riddle names are the map's zone names, so they must not contain the answer, part of it, or another
stop's answer. The build scans every printed string before the spoiler divider — cover, how to
play, map, acts, maker, every riddle name, stanza and hint — against every stop's `answer_name`
and `secret_terms`, and stops on a hit. The data fields (`evidence`, `action`, `decoy`, `review`)
are not printed and are not scanned.

Before rendering, each riddle passes a review (`references/spec-schema.md`, Riddle review): the
rubric items are recorded pass or fail in the spec, and a cold solver who has seen only the riddle
pages and map tries to name each stop (SKILL.md step 7). A riddle solved from its hint alone fails.
A riddle solved from its evidence by inference passes and is recorded as easy: an armchair solve
by a well-read reader is part of the pleasure, a giveaway is not.

## Answer pages

Two paragraphs. The first delivers the answer and its hard facts — dates, dimensions, maker,
commission. The second is the turn: what the stop reveals about the thread that the first paragraph did
not. Then two labelled blocks ("How to recognize it", "<Thread> connection") and one tinted "What to
notice" well. The walker reads the answer page after the hunt, so the notice looks back at what
they saw ("The canopy you stood under stops abruptly") or forward to a return visit ("Next time you
pass, count the lamps"), never at the spot now. The build stops on an on-site instruction in any
post-hunt text (see Information timing).

Numbers, spelled out in the prose where they read better, are the texture of these pages. So are
inversions: the grandest room behind the plainest wall, the famous doorway that is the wrong house.

Write each paragraph to the sources it will cite, and cite them: a paragraph is `{"text", "sources"}`
and a block is `(heading, text, [ids])`. If a sentence has no source behind it, it is colour, not
fact — keep it out of the answer page or find the source. Where the record holds a `weaker_claim`,
the prose says the weaker thing plainly ("the Handbook records the tradition and says proof is
lacking"), and may name the better source by name; that is a feature of the voice, not a hedge.

Photographs: landscape frames fill the answer-page image box; a portrait photograph prints small.
Prefer landscape, or accept the small image knowingly. Keep `modified` to one short clause; it
prints under the photograph.

## Front and back matter

- **Three acts** — the thread split into three named layers, two sentences each, naming no stop. This
  page is what makes six stops feel like one argument.
- **The maker** — three paragraphs on the person or subject, a facts table of 5–7 label/value pairs, and
  a pullquote that states the method in one line.
- **The treasure** — a first paragraph that lists the walk's concrete images in one sentence, a second
  that states what the reader now knows, then the fill-in notes fields.
- **Start** — picked by the map engine, not written: the corner of two named streets near circle 1,
  outside every circle, inside the map frame, carrying none of any stop's secret terms; corners of two
  main streets rank first, then the nearest. It prints as a hollow S marker with the label "Start",
  a legend entry, and the caption "Start: A and B" under the map, and the cold solver reads that
  caption. No leg is drawn from it, and the map draws no finish: the last stop is where the walk
  ends. The how-to-play notes do not give a start or finish of their own, and no note may describe a
  stop ("stop 1 is a living tree behind a barrier"). If a stop's street would make a bad start corner,
  add the street name to that stop's `secret_terms`.
- **Sources and credits** — generated from the `images` and `sources` records; you write only the
  intro and colophon. The intro says where the photographs come from and that each fact is tied to a
  numbered source. Written sources print numbered in record order with their URL, their `supports`
  statement and any `weaker_claim` as a "Note:", so put the sources in the order a reader would
  want them: the stops' main sources first, practical and local pages after. Record `supports` as
  the facts actually read, in a clause or two; it is the only place the reader sees what each
  source carried.

## Design system

Inherited from the Cellini original; change palette hues per book, never the structure.

- Cream parchment ground, one strong accent (material-appropriate: porphyry red for Rome, brown stone
  for Bath), a muted green or olive as the minor accent, charcoal body, antique gold for rules and
  ornaments.
- Display face Cormorant or EB Garamond; body Source Serif. Letterspaced small-caps kickers, centred
  display titles, `—— ◆ ——` diamond rules, a heavy double rule on cover and spoiler pages, folio with
  flanking diamonds.
- Page is 5.5 × 8.5 in so two pages print on one letter sheet; the engine pads to a multiple of 4 so it
  can be folded and stitched.
- Derive the palette from the material of the place. A limestone town and a porphyry city should not
  look the same.

## Map

The map is generated, not drawn, and it is generated from the interview inputs alone. Your job is
the inputs; `scripts/mapgen.py` decides pages, scale, framing, landmarks, labels and the café break.
Do not nudge anything to make a render look right. If it looks wrong, the input or the generator is
wrong; fix the input, or raise the generator problem.

What the map is for: getting your bearings between riddle stops. It is not for navigation. Keep it
sparse, as in the Cellini original: water, main streets, the route's streets, a landmark with a name
near each circle that a lost walker could type into a map app, and the circles themselves.

1. **Fetch data once** with `scripts/fetch_osm.py <dir>/data <bbox> [relation ids]`. Make the box
   cover every stop with a margin. List relation ids for river or park multipolygons that leave the
   box and for any stop whose target is a relation (a cathedral or square mapped as a multipolygon).
   Keep the manifest with the test.
2. **Targets.** Give each stop an OSM `target`, and a `view_from` street when the target is looked at
   rather than reached (a weir, a facade across a road). Read the OSM object to confirm it is the
   right thing.
3. **Secret terms.** Write them generously: the answer, its parts, its maker, and any building, street
   or square whose name gives it away. Those names never print, and no landmark is chosen from them.
   Do not include a word the zone name itself uses; the build will stop on it.
4. **Circles.** Leave `area_radius_ft` out unless the search needs a different size: smaller for a
   single object in a small square, larger for a facade or a stretch of road. Floor 100 ft. Two
   targets steps apart share one circle with `shares_area_with`.
5. **Stop names.** In a live book, use the riddle's name. Otherwise orient without pointing: relative
   position ("ACROSS THE RIVER"), not the object ("BY THE FOUNTAIN").
6. **Landmarks.** Leave `landmarks` out (automatic). The engine picks one named, recognisable
   feature within 500 ft of every circle; which one it picks does not matter, only that it has a
   name. Use `landmark_exclude` for a name that is wrong for the book, and a pinned list only for a
   test that must stay fixed.
7. **Café stop.** If the interview ticked Café stop, set `cafe_break: True`. The break names up to
   three real places just off the walk near halfway. Never hide food behind a riddle or a vague area.
8. **Order.** Ticketed and hours-limited stops last, and among them any stop where going in is
   required after any where it is optional. Write a fallback that keeps the walk worth doing if
   the last stop is shut. Prefer orders that do not double back past an earlier
   stop: `no_backtracking` steers later legs off streets already walked, and the build warns, naming
   the legs, when more than about 80 ft is retraced anyway. The book makes no promise about it.
9. **Units.** Imperial (feet and miles) in every book. It is not a choice: any other value stops
    the build.
10. **Notes.** Use placeholders for distance and time, so they always match the solved route. The
    settled wording: representation note "Drawn from OpenStreetMap data and simplified; north is up.
    For getting your bearings between riddle stops; use a map app for turn-by-turn directions.";
    route note "{stops} stops, about {distance_mi} miles and {minutes} minutes on foot. Each riddle's
    answer lies somewhere inside its circle."
11. **Pages and framing.** Leave `frame` out. A compact walk gets one page. A long walk, or one with a
    tight cluster and long legs, is split over up to three pages; each later page repeats the previous
    page's last stop with its circle. Circles grow (up to 400 ft) only when no plan keeps them at their
    set size, which happens on long legs between isolated stops. If no plan works, the build lists
    every page and constraint with a fix: shorten the legs, regroup the stops, or share a circle.
12. **Render the map alone first** with `scripts/build_map.py`. Read the `!! map warning` lines and the
    record: page plan, grown circles, chosen landmarks, café candidates, crossings, and anything
    placed by a fallback.

How it should look, settled in review:

- Compass and scale bar side by side in a corner, compass on the border side.
- One scale-bar value across pages where it reads; "Zoomed out from page N" under the bar whenever a
  page's scale changes.
- Landmarks styled the same whatever their kind.
- Every circle on every page it appears, including the carried-over stop.
- The café break on the page that draws its leg, with the café names in the caption.

The map still needs human review: does the geography match the sources, does the route agree with a
real walk, and does the drawn geography itself give an answer away (a round junction under a fountain
circle, a garden island under an obelisk circle)? The generator cannot judge semantic leaks.

## Information timing

Write each piece of text for the moment it is read.

| Moment | Pages | What belongs there |
| --- | --- | --- |
| Pre-walk | cover, How to Play (with the Before you go box), trail map, acts, maker | the rules, the route, the thread, access by stop number |
| On site | riddle pages, hints page | the riddle, then recognition help on the sealed hints page |
| Post-hunt | spoiler divider, answer pages, the treasure, sources and credits | the answer, its facts, and looking back |
| Any time | access-links page, inside the back cover | official links and stop names, read by choice |

Two rules follow. Nothing pre-walk or on site names an answer (the spoiler scans). Nothing post-hunt
asks the walker to do something at the stop: "Stand across the street" on an answer page arrives
after they have left. Write it as what they saw or as a reason to return.

## Access information

Walkers need to know before they leave whether anything is ticketed or has opening hours, without
the book telling them where the stops are. Three places hold it, each with one job:

- **Before you go box** (How to Play): generated. Stop numbers, kind, entry, one-line summary,
  checked date, fallback. Write the summary as the official page gives it ("Open daily to 8 p.m.,
  from 7 a.m. on weekdays"), never with the venue's name, its street or anything a secret term
  would catch. Write the fallback as an instruction ("come back another day for this one"), never
  as a place ("read the plaque by the south door" locates the stop as surely as its name).
- **Access-links page** (inside the back cover): generated. Names the stops and gives the official
  URLs. It is the one deliberate early spoiler in the book, labelled as such, kept at the back so a
  walker who has no need of it never meets it.
- **Notes** (hand-written): everything else practical (footwear, toilets, accessibility, weather).
  Never tickets, hours, prices or "free".

Read the official page on the day you write the summary, and again before printing: the build
warns after 30 days, and the record lists a human re-read as an unperformed check. Where the
venue's own documents disagree (a printed guide with older hours), follow the current hours page
and record the older figure as `weaker_claim`.

## Inspection before delivery

Read every page of the rendered PDF as an image. Check for: text clipped by the frame, paragraphs
overprinting each other, map labels that read ambiguously or sit nearer the wrong circle, a circle
missing from a page where its stop appears, a café label far from any drawn route, an answer image
squeezed to nothing, long URLs running past the text column on the credits page or the access-links
page, a hint printed on a riddle page, the hints page facing a riddle instead of the divider, and a
Before you go line that names, or narrows the place of, a stop, and answer-page text that still reads
as an instruction for the spot (the timing scan matches phrasing, not meaning). Fix the spec,
rebuild, and look again. Do not deliver a chapbook you have not seen rendered.
