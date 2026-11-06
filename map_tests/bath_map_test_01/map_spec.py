# -*- coding: utf-8 -*-
"""Map test 01 — Bath, five areas from the hot springs across the Avon.

Purpose: first fresh test of map schema v2 (backlog A10). Tests real river
geometry with a bridge crossing, a dense street network, open spaces, label
suppression where a street name is itself a giveaway, and a stop viewed from a
public street rather than visited. Not a reconstruction of The Stone City.

Targets are private: they drive area placement and the spoiler checks and never
print on the map. Sources for each target are listed under SOURCES below.
"""

PALETTE = {
    "paper":   "#F8F4E9",
    "ink":     "#272A26",
    "accent":  "#5B3A2E",
    "accent2": "#4A6455",
    "gold":    "#A98543",
    "water":   "#C5D6D8",
}

SPEC = {
    "slug": "bath_map_test_01",
    "author": "Chapbook Engine",
    "display_font": "Garamond",
    "palette": PALETTE,
    "title_line1": "BATH MAP TEST 01",
    "subtitle": "Springs to the River",
    "draft_label": "DRAFT · MAP TEST 01 · PENDING REVIEW",
    "map": {
        "version": 2,
        "representation": "geographic",
        "style": "bearings",
        # framing: the v2 draft (2026-10-11 22:57) at the same scale, shifted ~28 m east so the
        # Great Pulteney Street label fits; v2 exact was [-2.36295, 51.380101, -2.35429, 51.384434]
        "frame": {"bbox": [-2.36255, 51.380101, -2.35389, 51.384434]},
        "units": "imperial",
        "landmarks": [
            {"osm": "relation/2617911", "label": "ROMAN|BATHS"},
            {"osm": "way/122519644", "label": "GUILDHALL"},
            {"osm": "way/3027776", "label": "PARADE|GARDENS"},
            {"osm": "way/369771678", "label": "PULTENEY|BRIDGE"},
            {"road": "Great Pulteney Street", "label": "GREAT PULTENEY STREET"},  # road landmark for stop 5 (hand-picked; see backlog A14)
        ],
        "street_labels": [],
        "purpose": "orientation",
        "title": "Springs to the River",
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
            {"zone": "WEST OF|THE SPRINGS", "target": "way/2539",
             "answer_name": "Bath Street colonnades",
             "secret_terms": ["Bath Street", "colonnade", "colonnades", "Cross Bath", "Baldwin"],
             "access": "open_air", "area_radius_ft": 165},
            {"zone": "THE CHURCH|FORECOURT", "target": "way/39675782",
             "answer_name": "ladders of angels",
             "secret_terms": ["Abbey", "Abbey Churchyard", "angels", "ladder", "ladders",
                              "Jacob", "Oliver King"],
             "access": "open_air", "area_radius_ft": 130},
            {"zone": "EAST OF|THE CHURCH", "target": "node/3836624857",
             "answer_name": "Orange Grove obelisk",
             "secret_terms": ["Orange Grove", "obelisk", "Prince of Orange", "Alkmaar", "Nash"],
             "access": "open_air", "area_radius_ft": 100},
            {"zone": "ABOVE|THE WATER", "target": "way/48174917", "view_from": "way/52030084",
             "answer_name": "Pulteney Weir",
             "secret_terms": ["weir", "Pulteney Weir", "horseshoe"],
             "access": "open_air", "area_radius_ft": 150},
            {"zone": "ACROSS|THE RIVER", "target": "way/183745831",
             "answer_name": "Laura Place fountain",
             "secret_terms": ["Laura Place", "fountain", "Laura"],
             "access": "open_air", "area_radius_ft": 115},
        ],
    },
}

# Target provenance (read 2026-10-11). Map geometry: OpenStreetMap, see data/manifest.json.
SOURCES = {
    1: ["https://www.openstreetmap.org/way/2539",
        "https://en.wikipedia.org/wiki/Bath_Street,_Bath",
        "https://www.buildingconservation.com/articles/crossbath/crossbath.htm"],
    2: ["https://www.openstreetmap.org/way/39675782",
        "https://www.bathabbey.org/visiting/history/todays-abbey/"],
    3: ["https://www.openstreetmap.org/node/3836624857",
        "http://bath-heritage.co.uk/orange.html",
        "https://www.parksandgardens.org/places/orange-grove"],
    4: ["https://www.openstreetmap.org/way/48174917",
        "https://www.openstreetmap.org/way/52030084",
        "http://bath-heritage.co.uk/pulteney_weir.html"],
    5: ["https://www.openstreetmap.org/way/183745831",
        "https://en.wikipedia.org/wiki/Laura_Place,_Bath"],
}
