# Writing and design craft

## The one rule that cannot be broken

A riddle page must not reveal its own answer. Not in the riddle name, not in the stanzas, not in the
ornament, not in the map label, not in the hint. The map gives walking order and a broad zone only.
The reader's whole pleasure is the gap between "a room with no corners" and "the Circus".

Before rendering, reread every riddle page against the corresponding answer page and delete any proper
noun, dedication date, sculptor's name, or building name that gives it away. Street names in the
optional hint are acceptable; the answer's own name is not.

## Riddles

Three stanzas, in this progression:

1. **Position** — how to get there from the previous stop, in landscape terms. "Leave the square by its
   steepest corner and start to climb."
2. **Evidence** — two or three concrete, checkable observations the reader will see when standing
   there. Numbers are excellent: seven doors, five hundred emblems, a hundred and fourteen columns.
3. **Instruction** — a short imperative couplet that says what to find without naming it. "Find the
   circle the Elder did not live to see."

Lines run 6–11 words. Keep the register plain and slightly dry; no thee/thou, no forced rhyme. Rhyme
only if it arrives for free.

The hint is one or two prose sentences that make the answer findable without stating it, and should
name the decoy explicitly so the reader does not waste the walk.

## Answer pages

Two paragraphs. The first delivers the answer and its hard facts — dates, dimensions, maker,
commission. The second is the turn: what the stop reveals about the thread that the first paragraph did
not. Then two labelled blocks ("How to recognize it", "<Thread> connection") and one tinted "What to
notice" well containing a single instruction the reader can carry out on the spot.

Numbers, spelled out in the prose where they read better, are the texture of these pages. So are
inversions: the grandest room behind the plainest wall, the famous doorway that is the wrong house.

## Front and back matter

- **Three acts** — the thread split into three named layers, two sentences each, naming no stop. This
  page is what makes six stops feel like one argument.
- **The maker** — three paragraphs on the person or subject, a facts table of 5–7 label/value pairs, and
  a pullquote that states the method in one line.
- **The treasure** — a first paragraph that lists the walk's concrete images in one sentence, a second
  that states what the reader now knows, then the fill-in notes fields.

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
8. **Order.** Ticketed and hours-limited stops last. Avoid orders that double back past an earlier
   stop: the build stops on retracing when `no_backtracking` is set, and names the legs.
9. **Units.** `"imperial"` for US readers (feet and miles), `"metric"` otherwise.
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

## Inspection before delivery

Read every page of the rendered PDF as an image. Check for: text clipped by the frame, paragraphs
overprinting each other, map labels that read ambiguously or sit nearer the wrong circle, a circle
missing from a page where its stop appears, a café label far from any drawn route, an answer image
squeezed to nothing, and long URLs running past the text column on the credits page. Fix the spec,
rebuild, and look again. Do not deliver a chapbook you have not seen rendered.
