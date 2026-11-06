# -*- coding: utf-8 -*-
"""Template: a standalone schema-v2 map spec (bearings style), built from the interview inputs only.

Copy into a working directory with a data/ folder made by scripts/fetch_osm.py, replace the stops,
and render with scripts/build_map.py. Field reference: references/spec-schema.md; method: the Map
section of references/craft.md.

Each stop supplies what the interview and route research give: walking order, an OSM target, a zone
name, secret terms and access. Pages, scale, framing, landmarks ("auto"), circle growth and the café
break are left to the engine. Add "area_radius_ft" to a stop only when its search needs a different
size from the 130 ft default.

This is the Barcelona map test 03 fixture (map_tests/barcelona_map_test_03): 8 stops, the longest
interview option, with the Café stop option ticked. For a full book, put the "map" dict into the book
spec; its stops must match the book stops one for one, and each zone should be that stop's riddle
name. Targets are private: they place the circles and drive the spoiler checks, and never print.
"""

PALETTE = {
    "paper":   "#F7F1E6",
    "ink":     "#2A2724",
    "accent":  "#8A3B24",
    "accent2": "#3F5F66",
    "gold":    "#B48A3C",
    "water":   "#C3D7DC",
}

SPEC = {
    "slug": "barcelona_map_test_03",
    "author": "Chapbook Engine",
    "display_font": "Cormorant",
    "palette": PALETTE,
    "title_line1": "BARCELONA MAP TEST 03",
    "subtitle": "Old Town to the Unfinished Temple",
    "draft_label": "DRAFT · MAP TEST 03 · PENDING REVIEW",
    "map": {
        "version": 2,
        "representation": "geographic",
        "style": "bearings",
        "units": "imperial",
        "landmarks": "auto",
        "cafe_break": True,
        "street_labels": [],
        "purpose": "orientation",
        "title": "Old Town to the Unfinished Temple",
        "data": {"manifest": "data/manifest.json"},
        "route": {"mode": "foot", "avoid_steps": True, "no_backtracking": True},
        "representation_note": "Drawn from OpenStreetMap data and simplified; north is up. "
                               "For getting your bearings between riddle stops; use a map app "
                               "for turn-by-turn directions.",
        "route_note": "{stops} stops, about {distance_mi} miles and {minutes} minutes on foot. "
                      "Each riddle's answer lies somewhere inside its circle.",
        "mechanic_note": "The map gives you the order. The riddles reveal what, exactly, "
                         "you are meant to find.",
        "stops": [
            {"zone": "BEFORE THE|GREAT DOORS", "target": "relation/3298476",
             "answer_name": "Barcelona Cathedral façade",
             "secret_terms": ["Catedral", "Cathedral", "Santa Creu", "Santa Eulàlia", "Eulalia", "Seu"],
             "access": "open_air"},
            {"zone": "THE ROYAL|SQUARE", "target": "relation/18708616",
             "answer_name": "Plaça del Rei",
             "secret_terms": ["Plaça del Rei", "Rei", "Tinell", "Palau Reial"],
             "access": "open_air"},
            {"zone": "THE SAILORS'|NAVE", "target": "way/51260215",
             "answer_name": "Santa Maria del Mar",
             "secret_terms": ["Santa Maria del Mar", "Maria del Mar", "Basílica"],
             "access": "open_air"},
            {"zone": "UNDER THE|WAVES OF TILE", "target": "way/31957078",
             "answer_name": "Mercat de Santa Caterina roof",
             "secret_terms": ["Santa Caterina", "Caterina", "Miralles", "Tagliabue"],
             "access": "open_air"},
            {"zone": "WATER|AND GOLD", "target": "way/135115868",
             "answer_name": "Cascada of the Parc de la Ciutadella",
             "secret_terms": ["Cascada", "waterfall", "Fontserè", "Fontsere"],
             "access": "open_air"},
            {"zone": "THE RED|GATEWAY", "target": "way/377875377",
             "answer_name": "Arc de Triomf",
             "secret_terms": ["Arc de Triomf", "Triomf", "Triumph", "Vilaseca"],
             "access": "open_air"},
            {"zone": "THE DRAGON'S|BACK", "target": "relation/9427554",
             "answer_name": "Casa Batlló",
             "secret_terms": ["Batlló", "Batllo", "Gaudí", "Gaudi"],
             "access": "open_air"},
            {"zone": "THE UNFINISHED|ONE", "target": "relation/9194723",
             "answer_name": "Sagrada Família",
             "secret_terms": ["Sagrada", "Família", "Familia", "Gaudí", "Gaudi", "Expiatori"],
             "access": "ticketed"},
        ],
    },
}

# Target provenance. Map geometry: OpenStreetMap, see data/manifest.json.
SOURCES = {
    1: ["https://www.openstreetmap.org/relation/3298476"],
    2: ["https://www.openstreetmap.org/relation/18708616"],
    3: ["https://www.openstreetmap.org/way/51260215"],
    4: ["https://www.openstreetmap.org/way/31957078"],
    5: ["https://www.openstreetmap.org/way/135115868"],
    6: ["https://www.openstreetmap.org/way/377875377"],
    7: ["https://www.openstreetmap.org/relation/9427554"],
    8: ["https://www.openstreetmap.org/relation/9194723"],
}
