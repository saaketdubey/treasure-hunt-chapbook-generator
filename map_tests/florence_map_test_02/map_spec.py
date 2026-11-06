# -*- coding: utf-8 -*-
"""Map test 02 — Florence, the Cellini Trail, regenerated under the settled map rules.

Purpose: second fresh map test (backlog A10/A12). Reuses the five stops and order of
Cellini's Florence (approved 2026-10-12) as fixture inputs; the old book is not edited.
Tests a ticketed first stop under a recorded map-only waiver, two stops sharing one
circle, a target given by coordinates (no OSM object), a long riverside leg, and
hiding the names of places that hold targets.

Targets are private: they drive area placement and the spoiler checks and never print.
Sources for each target are listed under SOURCES below.
"""

PALETTE = {
    "paper":   "#FAF3E6",
    "ink":     "#2B2622",
    "accent":  "#8A2E22",
    "accent2": "#5E6B3C",
    "gold":    "#B08A4A",
    "water":   "#C9DCDC",
}

SPEC = {
    "slug": "florence_map_test_02",
    "author": "Chapbook Engine",
    "display_font": "Cormorant",
    "palette": PALETTE,
    "title_line1": "FLORENCE MAP TEST 02",
    "subtitle": "The Cellini Trail",
    "draft_label": "DRAFT · MAP TEST 02 · PENDING REVIEW",
    "map": {
        "version": 2,
        "representation": "geographic",
        "style": "bearings",
        "units": "imperial",
        # landmarks chosen by the generator from the map data
        "landmarks": "auto",
        "street_labels": [],
        "purpose": "orientation",
        "title": "The Cellini Trail",
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
            {"zone": "THE EAGLE'S|PRIZE", "target": "way/43837065",
             "answer_name": "Cellini, Ganymede",
             "secret_terms": ["Ganymede", "Ganimede", "Bargello"],
             "access": "ticketed", "area_radius_ft": 150,
             "order_waiver": "map test reproduces the Cellini's Florence route as written; "
                             "the book's stop order is backlog E work"},
            {"zone": "THE BRONZE|VICTOR", "target": "node/3391028129",
             "answer_name": "Cellini, Perseus with the Head of Medusa",
             "secret_terms": ["Perseus", "Perseo", "Medusa", "Loggia dei Lanzi", "Lanzi"],
             "access": "open_air", "area_radius_ft": 160},
            {"zone": "THE MAKER|IN MARBLE",
             "target_point": {
                 "lat": 43.76880, "lon": 11.25570, "verified": False,
                 "source": "https://en.wikipedia.org/wiki/Loggiato_of_the_Uffizi",
                 "note": "estimate: Cambi's Cellini statue is in a niche nearest the former Mint "
                         "(https://michelangelobuonarrotietornato.com/2025/09/21/"
                         "il-cellini-del-cambi-nella-loggia-degli-uffizi/), north part of the "
                         "Uffizi court; exact niche position not confirmed"},
             "shares_area_with": 2,
             "answer_name": "Ulisse Cambi, statue of Benvenuto Cellini",
             "secret_terms": ["Uffizi", "Piazzale degli Uffizi", "Cambi", "niche"],
             "access": "open_air"},
            {"zone": "THE GOLDSMITH'S|BRIDGE", "target": "node/1715896562",
             "answer_name": "Romanelli, bust of Benvenuto Cellini",
             "secret_terms": ["Ponte Vecchio", "bust", "fountain", "Romanelli",
                              "Benvenuto Cellini"],
             "access": "open_air", "area_radius_ft": 130},
            {"zone": "THE NAME ALONG|THE ARNO", "target": "way/30030781",
             "answer_name": "Lungarno Benvenuto Cellini",
             "secret_terms": ["Lungarno Benvenuto Cellini", "Benvenuto Cellini", "Lungarno"],
             "access": "open_air", "area_radius_ft": 250},
        ],
    },
}

# Target provenance (read 2026-10-12). Map geometry: OpenStreetMap, see data/manifest.json.
SOURCES = {
    1: ["https://www.openstreetmap.org/way/43837065",
        "https://en.wikipedia.org/wiki/Portraits_of_Benvenuto_Cellini"],
    2: ["https://www.openstreetmap.org/node/3391028129",
        "https://www.uffizi.it/en/video/the-loggia-dei-lanzi"],
    3: ["https://en.wikipedia.org/wiki/Loggiato_of_the_Uffizi",
        "https://michelangelobuonarrotietornato.com/2025/09/21/il-cellini-del-cambi-nella-loggia-degli-uffizi/"],
    4: ["https://www.openstreetmap.org/node/1715896562",
        "https://it.wikipedia.org/wiki/Monumento_a_Benvenuto_Cellini"],
    5: ["https://www.openstreetmap.org/way/30030781"],
}
