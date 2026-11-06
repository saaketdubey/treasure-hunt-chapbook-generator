# -*- coding: utf-8 -*-
"""Template: a full chapbook spec, THE STONE CITY — A Six-Stop Georgian Treasure Hunt (John Wood,
father and son). Copy it and replace the content. Every book section is complete; the map is a
placeholder, written separately from templates/map_spec_example.py."""

PALETTE = {
    "paper":   "#F8F4E9",
    "ink":     "#272A26",
    "accent":  "#5B3A2E",   # Bath stone shadow / warm brown
    "accent2": "#4A6455",   # park green
    "gold":    "#A98543",
    "water":   "#D3DCDA",
}

SPEC = {
    "slug": "the-stone-city",
    "author": "Chapbook Engine",
    "display_font": "Garamond",
    "palette": PALETTE,
    "cover_motif": "crescent",
    "blank_label": "Your Bath notes",

    "cover_kicker": "Bath · A Walking Hunt",
    "title_line1": "THE STONE",
    "title_line2": "CITY",
    "subtitle": "A Six-Stop Georgian Treasure Hunt",
    "subtitle_lines": ["A Six-Stop Georgian", "Treasure Hunt"],
    "cover_tagline_lines": ["A walking riddle trail through the Bath",
                            "invented by John Wood, father and son"],

    # ------------------------------------------------------------------
    "how_to_play": {
        "intro": "Welcome to a six-stop walking hunt through the Bath of John Wood the Elder and "
                 "his son, John Wood the Younger. Between them, over roughly fifty years, they "
                 "designed the upper town you are about to walk through — not as buildings but "
                 "as one continuous composition in stone.",
        "mechanic": "The walking order is already decided for you. Your challenge is the riddle: "
                    "at each numbered area, work out which street, square, terrace or building "
                    "you are meant to find, and what the Woods did to it.",
        "steps": [
            "Walk to the next numbered area on the map — the sequence is fixed.",
            "Read the riddle before searching.",
            "Use the surroundings and the optional hint if you need them.",
            "Mark the stop when you have found the answer.",
            "Do not turn to the answers until the hunt is complete.",
        ],
        "checklist_title": "The six riddles",
        "checklist": [
            "Stop 1 — The Name in the Grid",
            "Stop 2 — Seven Doors, One Palace",
            "Stop 3 — The Architect's Own Front Door",
            "Stop 4 — Five Hundred Small Riddles",
            "Stop 5 — The Plain Front, The Grandest Room",
            "Stop 6 — The Great Curve",
        ],
        "notes": [
            "Start: Wood Street  ·  Finish: Royal Crescent, via the Gravel Walk",
            "Roughly 1.5 km and about 30 minutes of walking \u2014 the shortest trail in the "
            "series, and the steepest, climbing steadily uphill",
            "Five stops are outdoors and free. The sixth, No. 1 Royal Crescent, is a ticketed "
            "museum and comes last, so you can decide when you get there",
            "No. 1 Royal Crescent is usually open Tuesday to Sunday, 10.00 to 17.30, last entry "
            "16.30, and closed on Mondays outside school holidays. Check before you travel",
            "Stop 5, the Bath Assembly Rooms, is an exterior stop: the building has been closed "
            "for a major restoration, so confirm the current position with the National Trust if "
            "you hope to get inside",
            "Most stops are working residential streets. Look up, and keep off private steps "
            "and railings",
            "Wear comfortable shoes and keep a map app open for practical navigation",
        ],
    },

    # ------------------------------------------------------------------
    # The map is not written here. Build it from templates/map_spec_example.py: fetch data with
    # scripts/fetch_osm.py, write the "map" dict for this book's stops (same count, same order,
    # each zone = that stop's riddle name), test it alone with scripts/build_map.py, then paste it
    # in place of this placeholder. The build stops until you do.
    "map": {"placeholder": True},

    # ------------------------------------------------------------------
    "acts": {
        "kicker": "How the city was made",
        "title_lines": ["Three Ways Bath", "Holds the Woods"],
        "lede": "Neither Wood left a statue or a famous tomb. They left the city itself, and it "
                "can be read in three layers.",
        "items": [
            {"numeral": "I", "name": "The Name",
             "text": "Start with the surname on a street sign and the square that made the "
                     "family's fortune. Before either Wood was an artist, he was a speculator "
                     "taking a very large financial risk on empty fields above the old town."},
            {"numeral": "II", "name": "The Geometry",
             "text": "Then read the plan: square, then circle, then crescent. Three simple "
                     "shapes, climbing the hill in sequence, joined by one straight street — a "
                     "piece of town planning disguised as a set of addresses."},
            {"numeral": "III", "name": "The Illusion",
             "text": "Finally, look at what the stone is pretending to be. Row after row of "
                     "ordinary houses wear the single unbroken front of a palace, and the "
                     "grandest interior in the city hides behind a plain portico."},
        ],
        "closer": "Three layers, six stops. The order is set for you; the riddles supply "
                  "the discoveries.",
    },

    # ------------------------------------------------------------------
    "maker": {
        "kicker": "Before the first riddle",
        "title_lines": ["Who Were", "the Woods?"],
        "standfirst": "A father and a son who treated a whole city as one building.",
        "paras": [
            "John Wood the Elder was born in Bath in 1704, the son of a local builder, and by "
            "his early twenties had worked on estates in Yorkshire and London. He came home with "
            "an idea far larger than any client had asked for: that Bath should be given an "
            "imperial forum, a grand circus and a gymnasium, a Roman city reborn in the local "
            "honey-coloured stone. He never persuaded anyone to fund that vision. Instead he "
            "built it piecemeal, as speculative housing, one leasehold at a time.",
            "His method was unusual and it is the key to everything you will see today. Wood "
            "leased land, designed a single monumental façade, then sublet the plots behind it to "
            "individual builders who had to construct their houses to fit his front. The result "
            "is a street of separate homes that reads as one palace — and, behind, a jumble of "
            "whatever each owner wanted. Bath still calls it Queen Anne fronts and Mary-Anne "
            "backs.",
            "John Wood the Younger, born in 1728, trained in the office and inherited the "
            "unfinished plan. He completed his father's streets, then took the geometry one step "
            "further with a crescent — a shape his father never built and the one the whole city "
            "is now known for. The father died in 1754, weeks after the first stone of his "
            "Circus was laid; the son finished it, and kept going for another twenty years.",
        ],
        "facts_title": "The short version",
        "facts": [
            ("The Elder", "John Wood, 1704–1754"),
            ("The Younger", "John Wood, 1728–1782"),
            ("Both", "Born and died in Bath"),
            ("Material", "Local Bath stone, oolitic limestone"),
            ("Method", "Speculative leasehold development"),
            ("Legacy", "Square · Circus · Crescent"),
        ],
        "pullquote": "They were not commissioned to design a city. They bought the land, drew "
                     "the fronts, and sold the space behind them.",
    },

    # ------------------------------------------------------------------
    "stops": [
        {
            "riddle": {
                "name": "The Name in the Grid",
                "stanzas": [
                    ["Begin below the first great square, in a street so short",
                     "you could miss it while looking for somewhere else."],
                    ["The houses copy the square around the corner because",
                     "the same man drew them — though these went up",
                     "long after he was in his grave."],
                    ["You are looking for a surname on a sign.",
                     "Read the street, not the buildings."],
                ],
                "ornament": "grid",
                "hint": "A short listed street immediately south-east of Queen Square. Photograph "
                        "the street sign.",
            },
            "answer": {
                "name": "The Name in the Grid",
                "subtitle_lines": ["Wood Street, Bath",
                                   "Designed by John Wood the Elder",
                                   "Built 1778 · Grade I listed"],
                "image": "bath1.jpg",
                "credit": "Wood Street, Bath. Photograph: Lewis Clarke (Wikimedia Commons, "
                          "CC BY-SA 2.0).",
                "paras": [
                    "Wood Street is a short street in central Bath, designed by John Wood the "
                    "Elder and built in 1778 in the same manner as the adjacent Queen Square. "
                    "Numbers 1 to 6 and 1A are listed Grade I as a group. The dates are worth a "
                    "second look: the Elder died in 1754, so this street went up more than twenty "
                    "years after his death, from his drawings — a reminder that the Woods sold "
                    "designs as much as buildings.",
                    "It is the quietest stop on the walk and the most easily missed, which is why "
                    "it comes first. Standing here you can see the whole method in miniature: a "
                    "modest terrace, deliberately matched to the grand composition around the "
                    "corner, extending one family's architectural grammar into an ordinary "
                    "address. Be careful with the story, though. The listing records confirm the "
                    "architect and the date but do not state why the street carries the name.",
                ],
                "blocks": [
                    ("How to recognize it", "A short street sign reading WOOD STREET, with a "
                     "terrace of pale Bath stone houses matching the style of Queen Square just "
                     "uphill."),
                    ("Wood connection", "The family surname in the everyday geography of the "
                     "city, on a street built to the Elder's design a generation after he died."),
                ],
                "notice": ("What to notice", "Compare the door surrounds and window proportions "
                           "here with the square you are about to enter. This is a rehearsal of "
                           "the same score, played quietly."),
            },
        },
        {
            "riddle": {
                "name": "Seven Doors, One Palace",
                "stanzas": [
                    ["Step uphill into the first of the three great shapes:",
                     "four sides, a garden, and traffic that ignores both."],
                    ["Stand on the south side and look north. You will think",
                     "you are facing one enormous house with a pediment.",
                     "Count the front doors. You will find seven."],
                    ["A spike in the garden was cut short by a storm.",
                     "Find the square that started the fortune."],
                ],
                "ornament": "square",
                "hint": "The first square uphill from Wood Street. Stand in the garden and face "
                        "the long palace-like range on the north side.",
            },
            "answer": {
                "name": "Seven Doors, One Palace",
                "subtitle_lines": ["Queen Square, Bath · John Wood the Elder",
                                   "Planned 1725, built from 1728",
                                   "North side: nos. 21–27"],
                "image": "bath2.jpg",
                "credit": "The obelisk in Queen Square, Bath. Photograph: Daderot (Wikimedia "
                          "Commons, CC0 / public domain).",
                "paras": [
                    "Queen Square was John Wood the Elder's first speculative development, drawn "
                    "in 1725 and built from 1728 — the project that made his reputation and his "
                    "money. The north side is the trick: numbers 21 to 27 are seven separate "
                    "townhouses, built by different hands, unified behind one Palladian front "
                    "with a central pediment and end pavilions. Nikolaus Pevsner called it one of "
                    "the finest Palladian compositions in England before 1730.",
                    "In the garden stands an obelisk raised by Beau Nash, Bath's celebrated "
                    "master of ceremonies, in 1738 to honour a royal visitor; a gale in 1815 "
                    "snapped the top, which is why the point looks blunt today. The west side is "
                    "later and by a different architect, John Pinch the Elder, in 1830 — so even "
                    "here the square is not the single object it pretends to be.",
                ],
                "blocks": [
                    ("How to recognize it", "A garden square with a truncated stone obelisk at "
                     "its centre and a long palace-fronted range with a triangular pediment on "
                     "the north side."),
                    ("Wood connection", "The Elder's first big gamble, and the invention of the "
                     "palace-front terrace that shapes the rest of this walk."),
                ],
                "notice": ("What to notice", "The seven doors under one pediment. Then look at "
                           "the roofline behind: the chimneys do not match, because the houses "
                           "behind the front never did."),
            },
        },
        {
            "riddle": {
                "name": "The Architect's Own Front Door",
                "stanzas": [
                    ["Leave the square by its steepest corner and start to climb",
                     "the street that ties all three shapes together."],
                    ["Halfway up, a much-visited doorway advertises a novelist",
                     "who lived at a different number entirely. Ignore it."],
                    ["Go back to the corner where you entered.",
                     "One of the two architects lived in this street. Find his house."],
                ],
                "ornament": "column",
                "hint": "The street climbing north out of Queen Square towards the Circus. The "
                        "house you want is number 41, on the Queen Square corner — not the "
                        "museum halfway up.",
            },
            "answer": {
                "name": "The Architect's Own Front Door",
                "subtitle_lines": ["Gay Street, Bath · No. 41",
                                   "Designed by John Wood the Elder from 1735,",
                                   "completed by John Wood the Younger"],
                "image": "bath3.jpg",
                "credit": "View up Gay Street, Bath, 28 August 2009. Photograph: NotFromUtrecht "
                          "(Wikimedia Commons, CC BY-SA 3.0).",
                "paras": [
                    "Gay Street is the connective tissue of Georgian Bath: the steep link from "
                    "Queen Square up to the Circus, begun by John Wood the Elder in 1735 and "
                    "completed by his son. The street is named after Robert Gay, a London surgeon "
                    "and Member of Parliament who owned the land the Woods leased — not, as "
                    "visitors often assume, after anyone who built it.",
                    "Number 41, on the Queen Square corner, was John Wood the Younger's own home. "
                    "Further up at number 40 is the Jane Austen Centre, which is why this street "
                    "is busy; Austen herself stayed at number 25. The famous doorway is the "
                    "decoy, and the architect's actual front door goes almost unphotographed, "
                    "a few paces from the square he inherited the job of finishing.",
                ],
                "blocks": [
                    ("How to recognize it", "The steep street running from Queen Square up to the "
                     "Circus. Your answer is the house on the Queen Square corner, number 41, "
                     "not the much-signposted museum uphill."),
                    ("Wood connection", "The Younger's own address, on a street his father began "
                     "and he finished."),
                ],
                "notice": ("What to notice", "Look along the pavement as you climb. The street "
                           "bends very slightly, so the Circus stays hidden until you are almost "
                           "in it. That concealment is deliberate."),
            },
        },
        {
            "riddle": {
                "name": "Five Hundred Small Riddles",
                "stanzas": [
                    ["Keep climbing until the street opens without warning",
                     "into a room with no corners at all."],
                    ["Three curved ranges, three roads out, and no way to see",
                     "the whole thing at once. Above the ground-floor columns",
                     "runs a band carved with hundreds of small emblems: serpents,",
                     "ships, acorns, masonic tools, nautical instruments."],
                    ["Its diameter was borrowed from a prehistoric ring of stones.",
                     "Find the circle the Elder did not live to see."],
                ],
                "ornament": "circle",
                "hint": "At the top of Gay Street. Stand in the middle of the space, look up at "
                        "the carved band above the lowest row of columns, then try to count it.",
            },
            "answer": {
                "name": "Five Hundred Small Riddles",
                "subtitle_lines": ["The Circus, Bath · John Wood the Elder",
                                   "Begun 1754, completed 1768",
                                   "Thirty houses in three segments"],
                "image": "bath4.jpg",
                "credit": "The Circus, Bath. Photograph: Adrian Pingstone (Wikimedia Commons, "
                          "public domain).",
                "paras": [
                    "The Circus is thirty houses forming a complete ring, divided into three "
                    "equal curved segments, each one facing an entrance road so that a visitor "
                    "arriving from any direction meets a continuous façade and never sees the "
                    "whole circle at once. Its outer diameter of about 318 feet was set close to "
                    "the 325-foot outer bank of Stonehenge, which Wood had surveyed and believed "
                    "to be a Druidic temple. He meant the resemblance.",
                    "The elevations stack three classical orders — Greek Doric below, Roman or "
                    "Composite in the middle, Corinthian above — and the Doric frieze carries "
                    "roughly five hundred and twenty-five carved pictorial emblems, from acorns "
                    "and serpents to masonic and nautical devices. The first stone was laid on 18 "
                    "February 1754 and John Wood the Elder died less than three months later; his "
                    "son built it. The five great plane trees in the middle arrived around 1820, "
                    "long after both men, and change the space completely.",
                ],
                "blocks": [
                    ("How to recognize it", "A full circle of pale terraced houses in three "
                     "segments, three roads entering it, a carved band of small emblems above the "
                     "lowest columns, and mature plane trees at the centre."),
                    ("Wood connection", "The Elder's masterpiece, laid out by him and finished by "
                     "his son after his death within the year."),
                ],
                "notice": ("What to notice", "Pick a stretch of the frieze and read ten emblems "
                           "in a row. No two repeat. Then look at the acorn finials on the "
                           "parapet — Wood's nod to the legend of Bladud and his pigs."),
            },
        },
        {
            "riddle": {
                "name": "The Plain Front, The Grandest Room",
                "stanzas": [
                    ["Leave the ring by its north-east road, a short street",
                     "that ends almost at once."],
                    ["Here is the dullest elevation on the whole walk:",
                     "a low portico, plain stone, nothing to photograph.",
                     "Behind it the son hid the largest Georgian interior in the city —",
                     "a hundred-foot ballroom lit by five chandeliers."],
                    ["The outside tells you nothing. That is the point.",
                     "Find the building that keeps its grandeur indoors."],
                ],
                "ornament": "keystone",
                "hint": "On Bennett Street, immediately north-east of the Circus. The answer is "
                        "the plain building with a columned porch, not the houses beside it.",
            },
            "answer": {
                "name": "The Plain Front, The Grandest Room",
                "subtitle_lines": ["Bath Assembly Rooms, Bennett Street",
                                   "John Wood the Younger, 1769–1771",
                                   "Grade I listed"],
                "image": "bath5.jpg",
                "credit": "Bath Assembly Rooms. Photograph: Colin Smith (Wikimedia Commons, "
                          "CC BY-SA 2.0).",
                "paras": [
                    "Built between 1769 and 1771 to John Wood the Younger's design, the Assembly "
                    "Rooms were the social engine of Georgian Bath: the place where visitors "
                    "danced, gambled, drank tea and inspected one another. The exterior is "
                    "deliberately reticent, a plain Doric portico on a plain stone block. Inside, "
                    "the Ballroom is over a hundred feet long with a ceiling more than forty feet "
                    "high and five chandeliers — the largest Georgian interior in Bath.",
                    "This is the inversion of everything else on the walk. Queen Square and the "
                    "Circus put palace fronts on ordinary houses; here the son put an ordinary "
                    "front on an extraordinary room. The building was gutted by bombing in 1942 "
                    "and restored afterwards, and it has more recently been closed for a major "
                    "restoration by the National Trust, so for this hunt the façade is the "
                    "answer. Check the current position before you plan an interior visit.",
                ],
                "blocks": [
                    ("How to recognize it", "A large, plain Bath stone building on Bennett Street "
                     "with a modest columned porch and very little decoration."),
                    ("Wood connection", "The Younger's public masterpiece, and the exact reverse "
                     "of the family's usual trick."),
                ],
                "notice": ("What to notice", "Stand across the street and try to guess the size "
                           "of the room behind the wall. Count the windows of the upper storey — "
                           "they are the only clue the outside gives you."),
            },
        },
        {
            "riddle": {
                "name": "The Great Curve",
                "stanzas": [
                    ["Go back through the ring and out along its west road,",
                     "then drop left onto a walled footpath through the gardens."],
                    ["The path delivers you to the shape the father never built:",
                     "not a square, not a circle, but an open arc",
                     "of more than a hundred columns and thirty front doors,",
                     "looking out over grass at nothing but sky."],
                    ["One house at the end has been furnished as it was.",
                     "Find the curve that finished the century."],
                ],
                "ornament": "crescent",
                "hint": "Follow Brock Street west from the Circus, or take the Gravel Walk. The "
                        "ticketed house museum sits at the eastern end of the arc.",
            },
            "answer": {
                "name": "The Great Curve",
                "subtitle_lines": ["Royal Crescent, Bath · John Wood the Younger",
                                   "1767–1774 · Thirty houses, 114 Ionic columns",
                                   "No. 1 Royal Crescent: house museum"],
                "image": "bath6.jpg",
                "credit": "Royal Crescent, Bath, 20 April 2005. Photograph: Adrian Pingstone "
                          "(Wikimedia Commons, public domain).",
                "paras": [
                    "Built between 1767 and 1774, the Royal Crescent is thirty terraced houses "
                    "swept into an arc about five hundred feet long, fronted by one hundred and "
                    "fourteen giant Ionic columns — each roughly two and a half feet in diameter "
                    "and forty-seven feet tall, carrying a five-foot entablature. It was the "
                    "first crescent of its kind in Britain and it completed the geometric "
                    "sequence his father had started: square, circus, crescent.",
                    "The illusion is at its most brazen here. Wood the Younger sold plots behind "
                    "a single fixed façade, so buyers commissioned whatever they liked behind it. "
                    "Walk around to the back and the unity collapses into a patchwork of "
                    "different heights, windows and extensions — Queen Anne fronts and Mary-Anne "
                    "backs. Number 1, at the eastern end, is now a museum furnished as a wealthy "
                    "Georgian household, and it is the one interior on this walk you can "
                    "reliably get into.",
                ],
                "blocks": [
                    ("How to recognize it", "A single sweeping arc of pale stone houses above an "
                     "open lawn, with a continuous row of tall Ionic columns and no break in the "
                     "front."),
                    ("Wood connection", "The Younger's finale, and the shape that made the "
                     "family's planning legible as one idea."),
                ],
                "notice": ("What to notice", "Look along the arc and then look at the roofline. "
                           "The front is one composition; the chimneys, dormers and rear walls "
                           "behind it are thirty separate arguments."),
            },
        },
    ],

    # ------------------------------------------------------------------
    "spoiler": {
        "title_lines": ["Stop Here—Unless", "the Hunt Is Complete"],
        "lede": "The pages that follow reveal every answer.",
        "check_title": "Before you continue, make sure you have:",
        "checks": ["Found all six stops", "Taken your photographs", "Made your guesses",
                   "Enjoyed the walk"],
    },

    "closing": {
        "kicker": "The end of the trail",
        "title_lines": ["The Treasure"],
        "paras": [
            "You began at a street sign and ended in front of a hundred and fourteen columns. "
            "Between them: seven doors pretending to be one house, an obelisk shortened by a "
            "storm, an architect's unphotographed front door, five hundred carved emblems that "
            "never repeat, and the plainest wall in Bath with the grandest room behind it.",
            "The treasure is the realisation that this city is not a collection of beautiful "
            "buildings. It is one argument, made in stone over fifty years by a father and a son "
            "who were never commissioned to make it — square, then circle, then crescent, "
            "climbing a hill, with ordinary houses hidden behind every palace front.",
        ],
        "notes_title": "Your Bath Notes",
        "note_fields": ["My favourite stop:", "My favourite carved detail:",
                        "A place to return to:", "Date completed:"],
        "pullquote": "Queen Anne fronts and Mary-Anne backs. Once you have seen one, you cannot "
                     "walk through Bath without checking.",
    },

    "credits": {
        "title_lines": ["Sources & Credits"],
        "intro": "Every photograph in this chapbook is a freely licensed file from Wikimedia "
                 "Commons, reproduced with its author and licence. Historical and practical "
                 "detail is drawn from the sources listed below. Opening hours and closures "
                 "change — confirm the Assembly Rooms and No. 1 Royal Crescent before you set "
                 "out.",
        "images": [
            "Stop 1 — Wood Street, Bath. Photograph: Lewis Clarke. CC BY-SA 2.0. "
            "commons.wikimedia.org/wiki/File:Wood_Street_Bath.jpg",
            "Stop 2 — Queen Square obelisk, Bath. Photograph: Daderot. CC0 / public domain. "
            "commons.wikimedia.org/wiki/File:Queen_Square_Obelisk_-_Bath,_England_-_DSC09716.jpg",
            "Stop 3 — View up Gay Street, Bath. Photograph: NotFromUtrecht. CC BY-SA 3.0. "
            "commons.wikimedia.org/wiki/File:View_up_Gay_Street_Bath.jpg",
            "Stop 4 — The Circus, Bath. Photograph: Adrian Pingstone. Public domain. "
            "commons.wikimedia.org/wiki/File:The.circus.bath.arp.jpg",
            "Stop 5 — Bath Assembly Rooms. Photograph: Colin Smith. CC BY-SA 2.0. "
            "commons.wikimedia.org/wiki/File:Bath_-_Assembly_Rooms_-_geograph.org.uk_-_5252321.jpg",
            "Stop 6 — Royal Crescent, Bath. Photograph: Adrian Pingstone. Public domain. "
            "commons.wikimedia.org/wiki/File:Royal.crescent.bath.arp.jpg",
        ],
        "sources": [
            "Wood Street, Bath — Wikipedia. en.wikipedia.org/wiki/Wood_Street,_Bath "
            "(John Wood the Elder; built 1778; Grade I listing of nos. 1A and 1–6).",
            "Queen Square, Bath — Wikipedia. en.wikipedia.org/wiki/Queen_Square,_Bath "
            "(plan of 1725; north side nos. 21–27; Pevsner's assessment; Beau Nash's obelisk of "
            "1738, truncated by a gale in 1815; west side by John Pinch, 1830).",
            "Gay Street, Bath — Wikipedia. en.wikipedia.org/wiki/Gay_Street,_Bath "
            "(begun by the Elder in 1735, completed by the Younger; no. 41 the Younger's home; "
            "named after Robert Gay; Jane Austen Centre at no. 40, Austen at no. 25).",
            "John Wood, the Elder — Wikipedia. en.wikipedia.org/wiki/John_Wood,_the_Elder "
            "(1704–1754; leasehold development method; Roman ambitions for Bath).",
            "John Wood, the Younger — Wikipedia. en.wikipedia.org/wiki/John_Wood,_the_Younger "
            "(1728–1782; Circus completion; Assembly Rooms; Royal Crescent).",
            "The Circus, Bath — Wikipedia. en.wikipedia.org/wiki/The_Circus,_Bath "
            "(thirty houses in three segments; 318 ft diameter against Stonehenge's 325 ft; "
            "stacked orders; c. 525 frieze emblems; first stone 18 February 1754; plane trees "
            "c. 1820).",
            "Bath Assembly Rooms — Wikipedia. en.wikipedia.org/wiki/Bath_Assembly_Rooms "
            "(1769–1771; Wood the Younger; Ballroom dimensions; 1942 bombing and restoration).",
            "Bath Assembly Rooms visitor information — National Trust. "
            "nationaltrust.org.uk/visit/bath-bristol/bath-assembly-rooms (current closure for "
            "restoration).",
            "Royal Crescent — Wikipedia. en.wikipedia.org/wiki/Royal_Crescent "
            "(1767–1774; thirty houses; 114 Ionic columns and their dimensions; 'Queen Anne "
            "fronts and Mary-Anne backs').",
            "No. 1 Royal Crescent — no1royalcrescent.org.uk/visit (opening days and times, "
            "last entry).",
        ],
        "colophon": "Set in EB Garamond and Source Serif 4. Printed double-sided on letter "
                    "paper, folded and stitched at the spine.",
    },
}
