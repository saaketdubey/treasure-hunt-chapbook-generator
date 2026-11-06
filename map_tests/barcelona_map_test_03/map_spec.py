# -*- coding: utf-8 -*-
"""Map test 03 — Barcelona, eight stops from the Gothic Quarter to the Sagrada Família.

Purpose: stress test of the map engine at the interview's longest option (8 stops, half
a day) with the Café stop option ticked. Dense medieval streets, a close pair of stops,
a park, and long legs across the Eixample grid. Inputs are what the interview and route
research would supply: stops, targets, zone names, secret terms and access. Circle sizes,
landmarks, pages and the café break are left to the engine.

Targets are private: they drive area placement and the spoiler checks and never print on
the map. Sources for each target are listed under SOURCES below.
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
