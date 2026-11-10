# The interview

Two `request_user_input` rounds, then get out of the way. The user is commissioning a chapbook, not
filling in a form. Skip any question the user has already answered; research answers the rest. Ask
nothing beyond these questions.

## Round 1 — four questions in one call

Put this intro in the round 1 `body`, verbatim, with the first line as a bold heading. Do not
reword it; the user approved this exact copy.

```text
Welcome to your Treasure Hunt
This makes a short booklet for a walking Treasure Hunt in a city of your choice. Each stop on the walk is a riddle, and solving it tells you what to look for. The answers, and the story behind each stop, are kept at the back behind a spoiler page.
There are two quick rounds: four questions now, then one more where you refine ideas for your hunt. Before anything is made, you'll see a short plan to approve.
At the end you'll get a PDF booklet to print or read on your phone, with a trail map, the riddles, the answers, and the sources.
```

1. **Place** — "In what city or town would you like to Treasure Hunt?" Free text. Keep this exact
   wording and capitalisation.
2. **Thread** — "What should the hunt follow?" Offer the four thread types below as options,
   strongest first, each with a one-line example. The place is not known yet, so use examples from
   other cities (Bernini in Rome; wool, glass or iron). Free text is accepted.
3. **Walk length** — "How long should the walk be?" Options: 4 stops / short (about half a mile, 30 min) ·
   6 stops / standard (about 1–2 miles, 45–60 min) · 8 stops / long (half a day).
4. **Include or avoid** — "Anything the walk should include or avoid?" Multi-select; say that
   leaving it blank means none. Options: Free and outdoor (no tickets or opening hours) · Easy
   walking (no steep climbs or stairs) · Kid-friendly (riddles children can solve) · Café stop (a
   place to eat or drink along the way).

Kid-friendly is the book's one difficulty setting: it sets `kid_friendly: True` in the spec and
changes how riddles are written and reviewed (`references/craft.md`, Riddles). Nothing else in the
interview sets difficulty; unset, riddles are written to one adult standard.

A blank answer to question 4 means no constraints. Defaults that apply without asking: one ticketed
or hours-limited finale is allowed, placed last, unless Free and outdoor is ticked; every route
avoids queues and peak-crowd bottlenecks. A gated finale is solved from outside (entry optional)
where the riddle allows it; entry is required only when the thing to find is indoors. No extra
question: the planner decides entry from the riddle and records it (`spec-schema.md`, Access).

## Round 2 — one question

5. **Specific thread** — offer exactly 3 concrete options for the chosen thread type in that place,
   each with a one-line description, plus a fourth option **"Show me 3 different options"**. Before
   offering an option, run a quick search to confirm it has enough surviving walkable stops for the
   chosen walk length (4, 6 or 8);
   never offer one that fails. If the user picks the reshuffle option, ask again with 3 new options
   that do not repeat earlier ones, until they choose. If the user typed a specific thread in round 1,
   skip round 2.

After round 2, summarise the plan, including the constraints and defaults that apply, and wait for
sign-off before researching or building.

## Thread types, in order of how well they work

1. **One maker, many works** — a sculptor, architect, printer, or engineer whose work survives in
   several places within walking distance. Strongest option: the stops accumulate into a portrait.
   Bernini in Rome, the Woods in Bath, Cellini in Florence.
2. **One material or trade** — glass, wool, silver, brick, water. Works where a city's wealth came
   from one thing and the traces are still visible.
3. **One event across a day or a week** — a fire, a siege, a flood, a coronation. Stops become a
   timeline and the order carries real tension.
4. **One idea in the plan** — geometry, defence, sanitation, processional route. Hardest to riddle
   because the answers are abstract; use only when the physical evidence is unmistakable.

Refuse nothing outright, but if the thread has fewer than four surviving walkable stops, say so and
propose the closest thread that does.

## Choosing stops

- Walking order is fixed. Prefer downhill or level; if the route must climb, say so in the
  practical notes.
- Every stop must be a specific findable object or address, not a vague area.
- Put any ticketed or hours-limited stop last so a closure cannot break the walk, and write its
  fallback (what to do if it is shut) at the same time.
- Deliberately exclude the single most famous site if it is a detour or a queue, and mention it as an
  optional prologue in the practical notes instead.
- Include at least one stop most visitors walk past, and at least one deliberate decoy — a nearby
  famous thing that is the wrong answer. The decoy belongs in the riddle and the answer page.
- Check the current status of every stop before writing. Closures, restorations and changed hours are
  the most common way one of these chapbooks goes wrong. For a gated stop, read the venue's own
  hours or tickets page and record it as a source; its access summary is written from that page.

## Sourcing and honesty

Every fact in the answer pages must come from a source you fetched and read, recorded in `sources`
with a full URL, the date read and what it supports, and cited by id from the claim that uses it.
Photographs must be freely licensed files from Wikimedia Commons, recorded in `images` with author
and licence as the file page states them. The credits page is generated from those records.

When the sources support a weaker claim than the appealing story, write the weaker claim in the
answer text and put the conflict in that source's `weaker_claim` field: what the other accounts say
and what the book therefore states. It prints in the credits, so the reader can see the seam. One
honest caveat is worth more than a confident invention.
