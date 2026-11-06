---
name: treasure-hunt-chapbook
description: "Produce a printable walking treasure-hunt chapbook for a city — riddle pages, a generated trail map from OpenStreetMap data, spoiler-gated answer pages, and sourced credits — as a stitched 5.5x8.5in PDF. Use for requests like a Rome or Bath treasure hunt booklet, a riddle walk zine, or another chapbook in the Cellini's Florence series. Not for ordinary itineraries, city guides, or map graphics without riddles."
license: MIT
compatibility: "Python with reportlab, Pillow and shapely. Fonts ship with the skill."
metadata:
  version: '1.7-draft'
---

# Treasure hunt chapbook

A chapbook is a small stitched booklet: a fixed walking route where the walking order is given and the
challenge is solving a riddle at each stop. The reader gets riddles first, answers only after a spoiler
divider. You write the content; `scripts/engine.py` owns every millimetre of layout.

Page order, always: cover · how to play · trail map · three acts · the maker · one riddle page per stop ·
spoiler divider · one answer page per stop · the treasure · sources and credits. The engine pads to a
multiple of 4.

## Procedure

1. **Interview.** Read `references/interview.md` and run its two-round interview: place, thread,
   length and include-or-avoid first; then three concrete thread options with a reshuffle. Skip
   questions the user has already answered.
2. **Research the route.** Choose the stops, verify each one's current status, and gather facts,
   freely licensed photographs with author and licence, and a full URL for every claim. Follow the
   sourcing rules in `references/interview.md`.
3. **Verify the evidence, then record it.** Before writing any prose, open every source URL and
   read it; open every photograph's Commons file page and confirm author, licence and that the
   downloaded file is the original (or note how it differs). Write what you found as `sources` and
   `images` records (`references/spec-schema.md`, Provenance). Where sources disagree or support
   less than the popular story, put that in the source's `weaker_claim` field now, so the prose is
   written to the weaker claim. A check you could not complete is recorded, not assumed.
4. **Set up.** Create a working directory with an `img/` subdirectory and download each stop photograph
   into it as `<slug><n>.jpg`. Fetch map data into `data/` with `scripts/fetch_osm.py` (large areas
   are fetched in tiles automatically), then read the Map section of `references/craft.md`.
5. **Write the map from the interview inputs only:** stops in walking order, an OSM target, zone
   name, secret terms and access per stop, and `cafe_break: True` if the interview ticked Café stop.
   Leave pages, landmarks, framing and circle growth to the engine. Start from
   `templates/map_spec_example.py` and render it alone with `scripts/build_map.py` until it builds.
6. **Write the spec.** Copy `templates/spec_example.py` into the working directory and replace its
   content, pasting in the map from step 5 and the records from step 3. Every answer paragraph,
   block and notice names the source ids it rests on. Read `references/spec-schema.md` for every
   field, and `references/craft.md` before writing any riddle, answer page, or palette.
7. **Review the riddles.** Fill each riddle's `evidence`, `action`, `decoy` and `review` rubric
   (`references/spec-schema.md`, Riddle review). Print the cold-solver packet with
   `python <skill>/scripts/riddle_pages.py <working-dir>/spec.py --skeleton`, give it to a reader
   who has not seen the spec or the answers (a separate agent in a fresh context will do), and
   record their answers in `cold_solver.json`. A stop named from its hint alone means the hint is
   rewritten and the read repeated.
8. **Check provenance live.** `python <skill>/scripts/verify_provenance.py <working-dir>/spec.py`
   fetches every source URL, checks each image against its Commons file page (author, licence,
   file hash) and writes `provenance_check.json` beside the spec. Fix mismatches in the records or
   the files; never in the check file. Re-run after any change to the records.
9. **Render.** `python <skill>/scripts/build_chapbook.py <working-dir>/spec.py`. It prints the output
   path and page count, and writes `<out>_record.json`: the claim-to-source ledger, the live checks,
   warnings and any unperformed checks. The build stops, without a PDF, on a claim with no source,
   a source no claim cites, an image without a verified record, a stale or missing check file, or a
   hand-written credits list; and on a riddle missing its data fields, a hint that locates, a failed
   rubric item without an override, or a missing, stale or hint-solved cold-solver report. Any
   `!! ... overflow` line means cut text; do not edit the engine to fit.
10. **Inspect every page** of the rendered PDF as an image, fix the spec, and rebuild until clean. The
   inspection checklist is at the end of `references/craft.md`. The map places its own labels and
   blocks the build on collisions, spoilers or a circle without a nearby landmark; review its record
   of page plan, grown circles, landmarks, cafés, crossings and warnings.
11. **Deliver** the PDF with `share_file`, named with the book's full title and subtitle, together
    with its `_record.json`.

Steps 9 and 10 repeat. You are done when you have looked at every page of the final render and found
nothing wrong.

## Non-negotiables

- A riddle page never reveals its own answer — not in its name, stanzas, ornament, hint, or map label.
  The map gives order, a circle per stop and nearby landmarks only.
- Every factual claim names its source ids, and every source is a record with a full URL, an access
  date and a `supports` statement of what was read there. Where the sources support only a weaker
  claim than the good story, write the weaker claim and record the conflict in `weaker_claim`.
- Photographs are freely licensed (accepted list in `scripts/provenance.py`), checked against their
  Commons file page, and credited by author and licence on the answer page and in the credits. The
  credits page is generated from the records; it is never written by hand.
- Riddles are solved by looking: evidence is observable at the stop's access level, the action
  produces the answer, the decoy is met without a detour, and the hint adds recognition, never
  location. The map circle is the only locator. Kid-friendly is the one difficulty setting.
- Three severities. Automated checks block the build. A blocked check may be overridden only with an
  `override` reason in the record, which prints in the build record. Reading the sources, judging
  factual support and matching image to record are human checks and stay with the author.
- Any ticketed or hours-limited stop goes last, with a "check before you travel" practical note.
- Food never sits behind a riddle: the café break names real places outright and is not a stop.

## Engine notes

- `Book(spec, out_path)` takes exactly those two arguments. `build()` returns the page count.
- `display_font` must be `"Cormorant"` or `"Garamond"`.
- `para()` returns the baseline of its last line, so advance by leading plus a small gap after it.
- The how-to-play notes list and the answer pages auto-shrink to fit; keep notes to 7 items or fewer.
- Extend the engine only to add a new riddle ornament shape, or as an approved backlog change. Layout
  changes affect every book in the series. Map generation lives in `scripts/mapgen.py` (schema v2,
  bearings style). After any map change, `map_tests/check_failures.py` in the project repo must
  still pass and the Bath, Florence and Barcelona map tests must still build.
