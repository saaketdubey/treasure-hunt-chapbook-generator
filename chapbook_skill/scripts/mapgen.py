"""
Map generation for chapbook trail maps (map schema v2).

Pipeline, in order:
  1. load cached OpenStreetMap data and verify it against its manifest
  2. resolve each stop's private target and public viewing way from OSM ids
  3. build a walking graph and solve the route leg by leg
  4. validate the route (order, access, crossings, claims); report retracing
  5. derive broad hunt areas that contain, but are not centred on, each target
  6. project real geometry (water, green, buildings, streets) into the map box
  7. place labels automatically: fixed type sizes, collision checks, priorities
  8. scan every map string against every stop's secret terms
  9. draw, then return a report of everything checked, dropped or suppressed

Nothing is nudged by hand and nothing is shrunk to fit. A required label that
cannot be placed, a route that cannot be solved, a secret term on the page or a
data file that does not match its manifest raises MapError and stops the build.

Requires: shapely >= 2.
"""
import gzip
import hashlib
import heapq
import json
import math
import os
import re
import xml.etree.ElementTree as ET

from shapely.geometry import (LineString, MultiLineString, MultiPolygon, Point,
                              Polygon, box as sbox)
from shapely.ops import linemerge, unary_union
from shapely import affinity

MAPGEN_VERSION = "2.1.0-draft.2"

# Type floors (points). Labels are never set below these; they are dropped or
# the build fails instead.
ZONE_LABEL_PT = 6.5
STREET_LABEL_PT = 6.0
FEATURE_LABEL_PT = 6.2
FURNITURE_PT = 6.0
SCALE_NOTE_RATIO = 0.10        # note a scale change from the previous page beyond this
MIN_LABEL_PT = 6.0
AREA_TINT = 0.86       # circle shading between the number disc and the dotted edge
LARGE_LANDMARK_X = 3.0 # landmarks larger than this many times the largest circle draw as faint outlines

FT = 0.3048
MIN_AREA_RADIUS_M = 100 * FT          # 100 ft
LANDMARK_REACH_M = 500 * FT            # every circle needs a landmark within this of its edge
DEFAULT_AREA_RADIUS_M = 130 * FT       # 130 ft
RETRACE_PENALTY = 3.0         # no_backtracking (routing preference): cost multiplier on edges an earlier leg walked
CARRY_MIN_PT = 7.6 + 3.5      # a carried-in circle always shows as a ring around its disc
CIRCLE_MAX_FT = 400           # circles may grow to this on pages that must print small
MAX_MAP_PAGES = 3
FURNITURE_SLIDE = 12          # points the scale/north group may move off its corner
DISC_R = 7.6                  # number disc radius, points
GAP_PT = 6.0                  # minimum clear paper between two circles
PANEL_PAD = 0.07              # extent padding used by the planner and the layout
MIN_CENTRE_OFFSET = 0.30      # area centre sits at least this fraction of r off the target
MAX_CENTRE_OFFSET = 0.55
WALK_KMH = 4.5
RETRACE_TOLERANCE_M = 25.0

MAJOR = {"trunk", "trunk_link", "primary", "primary_link", "secondary",
         "secondary_link", "tertiary", "tertiary_link"}
MINOR = {"residential", "unclassified", "living_street", "pedestrian", "service", "road"}
PATHS = {"footway", "path", "steps", "cycleway", "track", "bridleway"}
WALKABLE = MAJOR | MINOR | PATHS
STREET_WIDTH_PT = {"major": 3.0, "minor": 2.0, "service": 1.1, "path": 0.6}
FOOT_OK = {"yes", "designated", "permissive", "official"}


# ---- automatic landmarks: what kind of named feature helps a walker get their bearings.
# Weights rank kinds, not fame, so a city with no famous buildings still gets its parks,
# squares, schools, stations and main streets.
LANDMARK_KINDS = [
    ("historic", None, 3.0),
    ("amenity", {"place_of_worship", "townhall", "theatre", "library", "marketplace",
                 "arts_centre", "courthouse", "cinema"}, 3.0),
    ("tourism", {"museum", "gallery"}, 3.0),
    ("building", {"church", "cathedral", "chapel", "basilica", "mosque", "synagogue", "temple"}, 3.0),
    ("man_made", {"tower", "bridge", "lighthouse"}, 3.0),
    ("railway", {"station"}, 2.5),
    ("public_transport", {"station"}, 2.5),
    ("tourism", {"attraction", "viewpoint"}, 2.0),
    ("leisure", {"park", "garden", "stadium"}, 2.0),
    ("place", {"square"}, 2.0),
    ("highway", {"pedestrian"}, 2.0),          # named squares mapped as pedestrian areas
    ("amenity", {"university", "college", "school", "hospital"}, 1.5),
    ("shop", {"department_store", "mall"}, 1.0),
    ("building", None, 1.0),
    ("leisure", None, 1.0),
    ("amenity", None, 1.0),
]
ROAD_WEIGHT = {"major": 1.5, "minor": 1.0}
# café break (interview option): real named places just off the route near halfway
CAFE_KINDS = {("amenity", "cafe"): 3.0, ("shop", "bakery"): 2.5, ("shop", "pastry"): 2.5,
              ("amenity", "ice_cream"): 2.0, ("amenity", "restaurant"): 1.5}
CAFE_DETOUR_M = (75.0, 150.0)  # off-route distance tried: about 250 ft, then 500 ft
CAFE_PICKS = 3
CAFE_R = 3.6                  # café symbol radius, points
# start marker: a named street corner, picked automatically, outside every circle
START_REACH_M = 500 * FT      # the corner must be within this of circle 1's edge
START_R = 4.2                 # start symbol radius, points
START_CLEAR_M = 30.0          # the corner stays this far outside every circle's dotted edge
CAFE_SPACING_M = 40.0
LANDMARK_MIN_AREA_M2 = 150.0
LANDMARK_CANDIDATES_PER_CIRCLE = 6
ZONE_OPTIONS = 12             # best floated positions per stop name searched (plus half as many beside)
SEARCH_BUDGET = 60000         # placement search steps per map page
SET_BUDGET = 4000             # steps spent on the cheapest positions for one landmark set
LANDMARK_POSITIONS = 5        # label positions searched per landmark candidate


def landmark_weight(t):
    w = 0.0
    for key, vals, wt in LANDMARK_KINDS:
        v = t.get(key)
        if v and (vals is None or v in vals):
            w = max(w, wt)
    if w and (t.get("wikidata") or t.get("wikipedia")):
        w += 0.75
    return w


def auto_label(name):
    """Upper case; two lines at the space nearest the middle when long."""
    n = name.upper()
    if len(n) <= 14 or " " not in n:
        return n
    mid = len(n) / 2
    k = min((i for i, ch in enumerate(n) if ch == " "), key=lambda i: abs(i - mid))
    return n[:k] + "|" + n[k + 1:]


class MapError(Exception):
    pass


# ------------------------------------------------------------------ data

def _sha256(b):
    return hashlib.sha256(b).hexdigest()


def load_data(map_spec, base_dir, report):
    """Load the OSM files listed in the spec; verify each against the manifest."""
    d = map_spec["data"]
    man_path = os.path.join(base_dir, d["manifest"])
    if not os.path.exists(man_path):
        raise MapError(f"data manifest missing: {d['manifest']}")
    manifest = json.load(open(man_path))
    by_file = {f["file"]: f for f in manifest["files"]}
    data_dir = os.path.dirname(man_path)
    nodes, ways, rels = {}, {}, {}
    for f in manifest["files"]:
        path = os.path.join(data_dir, f["file"])
        raw = open(path, "rb").read()
        if path.endswith(".gz"):
            raw = gzip.decompress(raw)
        if _sha256(raw) != f["sha256_uncompressed"]:
            raise MapError(f"data file {f['file']} does not match its manifest hash")
        root = ET.fromstring(raw)
        for n in root.iter("node"):
            nodes[n.get("id")] = (float(n.get("lat")), float(n.get("lon")),
                                  {t.get("k"): t.get("v") for t in n.findall("tag")})
        for w in root.iter("way"):
            ways[w.get("id")] = ([nd.get("ref") for nd in w.findall("nd")],
                                 {t.get("k"): t.get("v") for t in w.findall("tag")})
        for r in root.iter("relation"):
            rels[r.get("id")] = ([(m.get("type"), m.get("ref"), m.get("role"))
                                  for m in r.findall("member")],
                                 {t.get("k"): t.get("v") for t in r.findall("tag")})
    report["data"] = {"manifest": d["manifest"], "files": list(by_file.values()),
                      "hash_check": "passed", "licence": manifest.get("licence"),
                      "attribution": manifest.get("attribution")}
    return nodes, ways, rels, manifest


class Proj:
    """Local equirectangular projection in metres. North is up by construction."""
    R = 6371008.8

    def __init__(self, lat0, lon0):
        self.lat0, self.lon0 = lat0, lon0
        self.k = math.cos(math.radians(lat0))

    def __call__(self, lat, lon):
        return (math.radians(lon - self.lon0) * self.R * self.k,
                math.radians(lat - self.lat0) * self.R)


def _way_xy(wid, ways, nodes, P):
    refs, _ = ways[wid]
    return [P(nodes[r][0], nodes[r][1]) for r in refs if r in nodes]


def _rings(way_ids, ways, nodes, P):
    """Join way segments end to end into closed rings."""
    segs = [_way_xy(w, ways, nodes, P) for w in way_ids if w in ways]
    segs = [s for s in segs if len(s) >= 2]
    rings = []
    while segs:
        cur = segs.pop(0)
        changed = True
        while changed and cur[0] != cur[-1]:
            changed = False
            for i, s in enumerate(segs):
                if s[0] == cur[-1]:
                    cur = cur + s[1:]
                elif s[-1] == cur[-1]:
                    cur = cur + s[::-1][1:]
                elif s[-1] == cur[0]:
                    cur = s[:-1] + cur
                elif s[0] == cur[0]:
                    cur = s[::-1][:-1] + cur
                else:
                    continue
                segs.pop(i)
                changed = True
                break
        if len(cur) >= 4 and cur[0] == cur[-1]:
            rings.append(cur)
    return rings


def _polys(pred, ways, rels, nodes, P, scan_ways=True):
    """Closed ways matching pred (when scan_ways) and multipolygon relations matching pred.
    Relation members are looked up in ways either way."""
    out = []
    for wid, (refs, tg) in (ways.items() if scan_ways else ()):
        if len(refs) >= 4 and refs[0] == refs[-1] and pred(tg):
            xy = _way_xy(wid, ways, nodes, P)
            if len(xy) >= 4:
                pg = Polygon(xy)
                if pg.is_valid and pg.area > 0:
                    out.append(pg)
    for rid, (mem, tg) in rels.items():
        if tg.get("type") == "multipolygon" and pred(tg):
            outer = _rings([m[1] for m in mem if m[0] == "way" and m[2] in ("outer", "")],
                           ways, nodes, P)
            inner = _rings([m[1] for m in mem if m[0] == "way" and m[2] == "inner"],
                           ways, nodes, P)
            for o in outer:
                pg = Polygon(o, [i for i in inner if Polygon(o).contains(Polygon(i))])
                if not pg.is_valid:
                    pg = pg.buffer(0)
                if pg.area > 0:
                    out.append(pg)
    return out


def is_water(t):
    return t.get("natural") == "water" or t.get("waterway") == "riverbank"


def street_class(t):
    h = t.get("highway")
    if h in MAJOR:
        return "major"
    if h == "service":
        return "service"
    if h in MINOR:
        return "minor"
    if h in PATHS:
        if t.get("footway") in ("sidewalk", "crossing") or t.get("indoor") == "yes":
            return None
        return "path"
    return None


# ------------------------------------------------------------------ resolve

def resolve(ref, nodes, ways, rels, P):
    """'node/123' or 'way/456' -> (x, y) metres, plus the OSM tags."""
    kind, oid = ref.split("/")
    if kind == "node":
        if oid not in nodes:
            raise MapError(f"{ref} not in cached data")
        lat, lon, tg = nodes[oid]
        return P(lat, lon), tg
    if kind == "way":
        if oid not in ways:
            raise MapError(f"{ref} not in cached data")
        xy = _way_xy(oid, ways, nodes, P)
        refs, tg = ways[oid]
        g = Polygon(xy) if refs[0] == refs[-1] and len(xy) >= 4 else LineString(xy)
        c = g.representative_point() if isinstance(g, Polygon) else g.interpolate(0.5, normalized=True)
        return (c.x, c.y), tg
    if kind == "relation":                      # multipolygon outline (large buildings, squares)
        if oid not in rels:
            raise MapError(f"{ref} not in cached data")
        tg = rels[oid][1]
        polys = _polys(lambda t: t is tg, ways, {oid: rels[oid]}, nodes, P, scan_ways=False)
        if not polys:
            raise MapError(f"{ref} has no complete outline in cached data; fetch it with fetch_osm.py")
        c = unary_union(polys).representative_point()
        return (c.x, c.y), tg
    raise MapError(f"unsupported OSM reference {ref}; use node/<id>, way/<id> or relation/<id>")


# ------------------------------------------------------------------ routing

def walk_graph(ways, nodes, P, avoid_steps):
    adj = {}
    edge_way = {}
    for wid, (refs, t) in ways.items():
        h = t.get("highway")
        if h not in WALKABLE:
            continue
        foot = t.get("foot")
        if foot in ("no", "private", "use_sidepath"):
            continue
        if t.get("access") in ("private", "no", "customers") and foot not in FOOT_OK:
            continue
        if t.get("indoor") == "yes" or t.get("area") == "yes" and h != "pedestrian":
            continue
        if avoid_steps and h == "steps":
            continue
        mult = 1.12 if h in MAJOR else 1.0
        pts = [r for r in refs if r in nodes]
        for a, b in zip(pts, pts[1:]):
            pa, pb = P(*nodes[a][:2]), P(*nodes[b][:2])
            d = math.dist(pa, pb)
            adj.setdefault(a, []).append((b, d * mult, d))
            adj.setdefault(b, []).append((a, d * mult, d))
            edge_way[frozenset((a, b))] = wid
    return adj, edge_way


def nearest_node(adj, nodes, P, xy, restrict=None):
    best, bd = None, 1e18
    cands = restrict if restrict is not None else adj.keys()
    for n in cands:
        if n not in adj:
            continue
        d = math.dist(P(*nodes[n][:2]), xy)
        if d < bd:
            best, bd = n, d
    return best, bd


def dijkstra(adj, src, dst, penalty=None):
    """Shortest walk; edges in penalty (frozenset pairs) cost RETRACE_PENALTY times more."""
    dist, prev, seen = {src: 0.0}, {}, set()
    h = [(0.0, src)]
    while h:
        d, u = heapq.heappop(h)
        if u in seen:
            continue
        if u == dst:
            break
        seen.add(u)
        for v, w, _ in adj.get(u, []):
            nd = d + (w * RETRACE_PENALTY if penalty and frozenset((u, v)) in penalty else w)
            if nd < dist.get(v, 1e18):
                dist[v], prev[v] = nd, u
                heapq.heappush(h, (nd, v))
    if dst not in dist:
        return None
    path = [dst]
    while path[-1] != src:
        path.append(prev[path[-1]])
    return path[::-1]


# ------------------------------------------------------------------ text helpers

def term_hits(text, terms):
    hits = []
    for t in terms:
        if re.search(r"(?<![A-Za-z])" + re.escape(t) + r"(?![A-Za-z])", text, re.I):
            hits.append(t)
    return hits


def stop_terms(st):
    return [t for t in ([st.get("answer_name")] + list(st.get("secret_terms", []))) if t]


def spoiler_scan(texts, stops):
    """texts: list of (where, string). Returns list of error strings."""
    errs = []
    for where, s in texts:
        if not s:
            continue
        for i, st in enumerate(stops, 1):
            for h in term_hits(s.replace("|", " "), stop_terms(st)):
                errs.append(f"spoiler: {where} contains '{h}' (secret term for stop {i})")
    return errs


def fill_placeholders(s, facts):
    try:
        return s.format(**facts)
    except KeyError as e:
        raise MapError(f"unknown placeholder {e} in map note")


# ------------------------------------------------------------------ main model

class MapModel:
    """Everything needed to draw one map, in metres, plus the validation report."""

    def __init__(self, map_spec, base_dir, slug="map"):
        self.m = map_spec
        self.report = {"generator": MAPGEN_VERSION, "errors": [], "warnings": [],
                       "labels": {"placed": [], "dropped": [], "suppressed": []},
                       "automated_checks": [], "unperformed_checks": [
                           "human review of rendered geography against read sources",
                           "physical half-letter print check",
                           "actual phone presentation check",
                           "on-site walk of the solved route",
                           "semantic (non-literal) spoiler review",
                       ]}
        rep = self.report
        if map_spec.get("placeholder"):
            raise MapError("map not written yet: build it from templates/map_spec_example.py, test it "
                           "with scripts/build_map.py, and paste it into the book spec")
        if map_spec.get("version") != 2:
            raise MapError("map schema v2 required; the v1 hand-placed schematic schema is retired")
        if map_spec.get("representation", "geographic") != "geographic":
            raise MapError("only representation='geographic' is supported")
        self.nodes, self.ways, self.rels, self.manifest = load_data(map_spec, base_dir, rep)
        rep["automated_checks"].append("data files match manifest SHA-256")
        stops = map_spec["stops"]
        if len(stops) < 2:
            raise MapError("a trail map needs at least two stops")

        # projection centred on the targets
        lat_lon = []
        for i, st in enumerate(stops, 1):
            if "target_point" in st:
                tp = st["target_point"]
                if not str(tp.get("source", "")).startswith("http"):
                    raise MapError(f"stop {i}: target_point needs a source URL")
                lat_lon.append((float(tp["lat"]), float(tp["lon"])))
                continue
            if "target" not in st:
                raise MapError(f"stop {i}: needs a target (OSM id) or a target_point")
            kind, oid = st["target"].split("/")
            if (kind == "node" and oid not in self.nodes) or (kind == "way" and oid not in self.ways) \
                    or (kind == "relation" and oid not in self.rels) or kind not in ("node", "way", "relation"):
                raise MapError(f"stop {i}: target {st['target']} not found in cached OSM data")
            if kind == "node":
                lat_lon.append(self.nodes[oid][:2])
            else:
                wids = [oid] if kind == "way" else [m[1] for m in self.rels[oid][0]
                                                     if m[0] == "way" and m[2] in ("outer", "") and m[1] in self.ways]
                rr = [r for w_ in wids for r in self.ways[w_][0] if r in self.nodes]
                if not rr:
                    raise MapError(f"stop {i}: target {st['target']} has no geometry in cached OSM data")
                lat_lon.append((sum(self.nodes[r][0] for r in rr) / len(rr),
                                sum(self.nodes[r][1] for r in rr) / len(rr)))
        self.P = Proj(sum(a for a, _ in lat_lon) / len(lat_lon),
                      sum(b for _, b in lat_lon) / len(lat_lon))
        P = self.P

        # targets, viewing ways, access policy
        self.targets, self.view_nodes = [], []
        r_cfg = map_spec.get("route", {})
        self.adj, self.edge_way = walk_graph(self.ways, self.nodes, P,
                                             r_cfg.get("avoid_steps", True))
        # stops snap only to the main walking network, never to an isolated fragment
        # (a footpath mapped inside a building, a private courtyard)
        main, seen_all = set(), set()
        for start in self.adj:
            if start in seen_all:
                continue
            comp, stack = {start}, [start]
            while stack:
                u = stack.pop()
                for v, _, _ in self.adj.get(u, []):
                    if v not in comp:
                        comp.add(v)
                        stack.append(v)
            seen_all |= comp
            if len(comp) > len(main):
                main = comp
        self.main_net = main
        for i, st in enumerate(stops, 1):
            if "target_point" in st:
                tp = st["target_point"]
                xy = P(float(tp["lat"]), float(tp["lon"]))
                rep.setdefault("target_points", []).append(
                    {"stop": i, "lat": tp["lat"], "lon": tp["lon"], "source": tp["source"],
                     "verified": bool(tp.get("verified", False)), "note": tp.get("note", "")})
                if not tp.get("verified", False):
                    rep["warnings"].append(f"stop {i}: target position given by coordinates and not "
                                           f"verified on site; the circle may not contain the target")
            else:
                xy, tg = resolve(st["target"], self.nodes, self.ways, self.rels, P)
            self.targets.append(xy)
            view = st.get("view_from")
            restrict = None
            if view:
                kind, oid = view.split("/")
                if kind != "way" or oid not in self.ways:
                    raise MapError(f"stop {i}: view_from {view} not a cached way")
                restrict = [r for r in self.ways[oid][0] if r in self.main_net]
                if not restrict:
                    raise MapError(f"stop {i}: view_from {view} is not walkable "
                                   f"(private, no foot access, or steps excluded)")
            n, d = nearest_node(self.adj, self.nodes, P, xy,
                                restrict if restrict is not None else self.main_net)
            if n is None or d > 120:
                raise MapError(f"stop {i}: no walkable point within 120 m of target")
            self.view_nodes.append(n)
        acc = [st.get("access", "open_air") for st in stops]
        for i, a in enumerate(acc[:-1], 1):
            if a in ("ticketed", "hours_limited"):
                waiver = stops[i - 1].get("order_waiver")
                if waiver:   # map-only tests; a full book build refuses waivers
                    rep["warnings"].append(f"route: stop {i} is {a} but is not the last stop; "
                                           f"waived for this map test: {waiver}")
                    rep.setdefault("waivers", []).append({"stop": i, "rule": "ticketed stops last",
                                                          "reason": waiver})
                else:
                    rep["errors"].append(f"route: stop {i} is {a} but is not the last stop")
        rep["automated_checks"].append("ticketed / hours-limited stops come last")

        # route legs
        self.legs = []
        used = {}
        total = 0.0
        for i in range(len(stops) - 1):
            path = dijkstra(self.adj, self.view_nodes[i], self.view_nodes[i + 1],
                            penalty=used if r_cfg.get("no_backtracking") else None)
            if path is None:
                raise MapError(f"route: no walkable path from stop {i+1} to stop {i+2}")
            xy = [P(*self.nodes[n][:2]) for n in path]
            length = sum(math.dist(a, b) for a, b in zip(xy, xy[1:]))
            total += length
            for a, b in zip(path, path[1:]):
                used.setdefault(frozenset((a, b)), set()).add(i)
            self.legs.append({"from": i + 1, "to": i + 2, "nodes": path, "xy": xy,
                              "length_m": round(length, 1),
                              "crossings": self._crossings(path)})
        # in and out of a stop down the same dead end is visiting it, not backtracking: edges
        # walked by consecutive legs within that stop's search radius of its target are exempt
        def _rad(st):
            return float(st["area_radius_ft"]) * FT if "area_radius_ft" in st else \
                DEFAULT_AREA_RADIUS_M

        def _visit(e, legs):
            if len(legs) != 2 or abs(max(legs) - min(legs)) != 1:
                return False
            k = max(legs)                      # stop index between the two legs
            r = _rad(stops[k])
            return all(math.dist(P(*self.nodes[v][:2]), self.targets[k]) <= r for v in e)
        for e in [e for e, lg in used.items() if len(lg) > 1 and _visit(e, lg)]:
            del used[e]
        retrace = sum(math.dist(P(*self.nodes[a][:2]), P(*self.nodes[b][:2]))
                      for e, legs in used.items() if len(legs) > 1 for a, b in [tuple(e)])
        self.total_m = total
        rep["route"] = {"total_m": round(total, 1), "retrace_m": round(retrace, 1),
                        "avoid_steps": r_cfg.get("avoid_steps", True),
                        "legs": [{k: v for k, v in L.items() if k not in ("nodes", "xy")}
                                 for L in self.legs]}
        # retracing is reported, never claimed: the book makes no backtracking promise (E6)
        if retrace > RETRACE_TOLERANCE_M:
            pairs = sorted({tuple(sorted(lg)) for lg in used.values() if len(lg) > 1})
            which = ", ".join(f"legs {a + 1}→{a + 2} and {b + 1}→{b + 2}" for a, b, *_ in pairs)
            rep["warnings"].append(f"route: retraces {retrace:.0f} m ({which}); reorder the stops if "
                                   f"that walk reads badly")
        for L in self.legs:
            for c in L["crossings"]:
                if c["control"] in ("unmarked", "unknown"):
                    rep["warnings"].append(
                        f"route: leg {L['from']}→{L['to']} crosses {c['road']} "
                        f"with {c['control']} crossing data; check on site")
        if "claimed_distance_m" in r_cfg:
            rep["errors"].append("route: `claimed_distance_m` is retired; give the claim in feet "
                                 "as `claimed_distance_ft`")
        claimed = r_cfg.get("claimed_distance_ft")
        if claimed and abs(claimed * FT - total) / total > 0.15:
            rep["errors"].append(f"route: claimed {claimed} ft but solved route is "
                                 f"{total / FT:.0f} ft")
        rep["automated_checks"] += ["every leg solved on the OSM walking network",
                                    "retracing measured and reported",
                                    "major-road crossings listed with crossing data"]

        # every book uses imperial units (feet and miles); it is not a per-book choice
        self.units = map_spec.get("units", "imperial")
        if self.units != "imperial":
            raise MapError(f"units {self.units!r} not supported: every book uses imperial units "
                           "(feet and miles)")
        self.numbers = list(range(1, len(stops) + 1))
        self.ghosts = set()
        # shared circles: a stop may share the previous stop's circle when the two are steps apart
        self.group = list(range(len(stops)))
        for i, st in enumerate(stops, 1):
            k = st.get("shares_area_with")
            if k is None:
                continue
            if k != i - 1:
                raise MapError(f"stop {i}: shares_area_with must name the stop just before it ({i - 1})")
            self.group[i - 1] = self.group[k - 1]
        # hunt areas
        self.areas = self._areas(stops, slug)
        for j, (cx, cy, r) in enumerate(self.areas, 1):
            for L in self.legs:
                if self.group[j - 1] in (self.group[L["from"] - 1], self.group[L["to"] - 1]):
                    continue
                if any(math.dist(p, (cx, cy)) < r for p in L["xy"]):
                    when = "before its turn" if j > L["to"] else "again after it was visited"
                    rep["warnings"].append(
                        f"route: leg {L['from']}→{L['to']} passes through area {j} {when}")
        rep["automated_checks"].append("hunt areas contain targets, are off-centre, do not overlap")

        facts = {"distance_mi": f"{total/1609.344:.1f}", "distance_ft": f"{round(total / FT, -1):.0f}",
                 "minutes": f"{max(5, int(5 * round(total / 1000 / WALK_KMH * 60 / 5)))}",
                 "stops": str(len(stops))}
        self.facts = facts
        self.notes = {k: fill_placeholders(map_spec.get(k, ""), facts)
                      for k in ("route_note", "mechanic_note", "representation_note")}
        for k, v in self.notes.items():
            raw = map_spec.get(k, "")
            if re.search(r"\d", re.sub(r"\{[a-z_]+\}", "", raw)):
                rep["warnings"].append(f"{k}: contains a hard-coded number; derive it from the route")
        rep["automated_checks"].append("route-note figures derived from the solved route")

        self.streets_all = []
        for wid, (refs, t) in self.ways.items():
            cls = street_class(t)
            if not cls or t.get("area") == "yes":
                continue
            xy = _way_xy(wid, self.ways, self.nodes, P)
            if len(xy) >= 2:
                self.streets_all.append((cls, LineString(xy), t.get("name"), t.get("bridge") == "yes", wid))
        # style, route ways, landmarks
        # one style: sparse "bearings" base (main streets, route streets, chosen landmarks)
        if map_spec.get("style", "bearings") != "bearings":
            raise MapError(f"map style {map_spec.get('style')!r} is retired; only \"bearings\" is supported")
        self.style = "bearings"
        self.route_ways = {self.edge_way[frozenset((a, b))] for L in self.legs
                           for a, b in zip(L["nodes"], L["nodes"][1:])}
        self.landmarks = []
        big = max(math.pi * r * r for _, _, r in self.areas)
        self.auto_landmarks = map_spec.get("landmarks", "auto") == "auto"
        self.landmark_pool = self._landmark_pool(big) if self.auto_landmarks else []
        for k, lm in enumerate(map_spec.get("landmarks", []) if not self.auto_landmarks else [], 1):
            if "road" in lm:
                parts = [ln for cls, ln, name, br, wid in self.streets_all if name == lm["road"]]
                if not parts:
                    raise MapError(f"landmark {k}: no mapped road named {lm['road']!r}")
                self.landmarks.append({"label": lm.get("label", lm["road"].upper()), "kind": "road",
                                       "osm": f"road:{lm['road']}", "name": lm["road"],
                                       "poly": unary_union(parts)})
                continue
            poly = self._element_poly(lm["osm"])
            if poly is None:
                raise MapError(f"landmark {k}: {lm['osm']} has no closed outline in cached data")
            faint = poly.area > LARGE_LANDMARK_X * big
            self.landmarks.append({"label": lm["label"], "osm": lm["osm"], "poly": poly,
                                   "kind": "outline", "faint": faint})
            if faint:
                rep.setdefault("faint_landmarks", []).append(lm["label"].replace("|", " "))
        self.cafes = self._cafe_break() if map_spec.get("cafe_break") else []
        self.start = self._start_point()
        self.street_label_list = map_spec.get("street_labels")
        for j, (cx, cy, r) in enumerate(self.areas, 1):
            if self.group[j - 1] != j - 1:
                continue
            circ = Point(cx, cy).buffer(r, 48)
            near = [(lm["poly"].distance(circ), lm["label"])
                    for lm in (self.landmark_pool if self.auto_landmarks else self.landmarks)]
            best = min(near) if near else None
            if not best or best[0] > LANDMARK_REACH_M:
                rep["errors"].append(f"landmark: circle {j} has no landmark within 500 ft of its edge"
                                     + (f" (nearest {best[1].replace('|', ' ')}, "
                                        f"{best[0] / FT:.0f} ft)" if best else ""))
            else:
                rep.setdefault("landmark_reach", []).append(
                    {"circle": j, "landmark": best[1].replace("|", " "), "ft_from_edge": round(best[0] / FT)})
        rep["automated_checks"].append("every circle has a landmark within 500 ft of its edge")

        # geography
        self.water = _polys(is_water, self.ways, self.rels, self.nodes, P)
        self.streets = self.streets_all
        self.rivers = []
        for wid, (refs, t) in self.ways.items():
            if t.get("waterway") == "river":
                xy = _way_xy(wid, self.ways, self.nodes, P)
                if len(xy) >= 2:
                    self.rivers.append((t.get("name"), LineString(xy)))

        # zone and note spoiler checks
        texts = [("map title", map_spec.get("title", ""))]
        texts += [(f"map {k}", v) for k, v in self.notes.items()]
        texts += [(f"zone label {i}", st["zone"]) for i, st in enumerate(stops, 1)]
        texts += [(f"landmark {lm['osm']}", lm["label"]) for lm in self.landmarks]
        texts += [("street label", n) for n in (self.street_label_list or [])]
        rep["errors"] += spoiler_scan(texts, stops)
        rep["automated_checks"].append("map title, notes and zone labels scanned for every stop's secret terms")

    def _landmark_pool(self, big):
        """Every named feature that could serve as a landmark, screened and measured against
        each circle. Selection happens at layout time, where label room is known."""
        stops = self.m["stops"]
        secrets = [(i, stop_terms(st)) for i, st in enumerate(stops, 1)]
        extra = list(self.m.get("landmark_exclude", []))
        target_refs = {st.get("target") for st in stops if st.get("target")}
        tpts = [Point(xy) for xy in self.targets]
        circles = [(j, Point(cx, cy).buffer(r, 48)) for j, (cx, cy, r) in enumerate(self.areas)
                   if self.group[j] == j]
        rep = self.report
        excluded, pool = [], {}

        def consider(ref, tags, geom, kind, weight, size):
            name = tags.get("name")
            dists = {j: geom.distance(c) for j, c in circles}
            if min(dists.values()) > LANDMARK_REACH_M:
                return
            why = None
            if ref in target_refs:
                why = "is a stop's target"
            elif kind == "outline" and any(geom.buffer(5).contains(p) for p in tpts):
                why = "holds a stop's target"
            else:
                for i, terms in secrets:
                    h = term_hits(name, terms)
                    if h:
                        why = f"matches secret term '{h[0]}' for stop {i}"
                        break
                if not why and term_hits(name, extra):
                    why = "excluded by spec"
            if why:
                excluded.append({"name": name, "osm": ref, "reason": why})
                return
            cand = {"label": auto_label(name), "name": name, "osm": ref, "poly": geom, "kind": kind,
                    "faint": kind == "outline" and geom.area > LARGE_LANDMARK_X * big,
                    "weight": weight, "size": size, "dists": dists}
            prev = pool.get(name.lower())
            if prev is None or (weight, size) > (prev["weight"], prev["size"]):
                pool[name.lower()] = cand

        for wid, (refs, t) in self.ways.items():
            if not t.get("name") or len(refs) < 4 or refs[0] != refs[-1]:
                continue
            w = landmark_weight(t)
            if not w or (t.get("highway") and t.get("highway") != "pedestrian"):
                continue
            if t.get("highway") == "pedestrian" and t.get("area") != "yes":
                continue
            xy = _way_xy(wid, self.ways, self.nodes, self.P)
            if len(xy) < 4:
                continue
            pg = Polygon(xy)
            if not pg.is_valid:
                pg = pg.buffer(0)
            if pg.area >= LANDMARK_MIN_AREA_M2:
                consider(f"way/{wid}", t, pg, "outline", w, pg.area)
        for rid, (mem, t) in self.rels.items():
            if not t.get("name") or t.get("type") != "multipolygon":
                continue
            w = landmark_weight(t)
            if not w:
                continue
            polys = _polys(lambda tg: tg is t, self.ways, {rid: self.rels[rid]}, self.nodes, self.P,
                           scan_ways=False)
            if polys:
                g = unary_union(polys)
                if g.area >= LANDMARK_MIN_AREA_M2:
                    consider(f"relation/{rid}", t, g, "outline", w, g.area)
        roads = {}
        for cls, ln, name, br, wid in self.streets_all:
            if name and cls in ROAD_WEIGHT:
                r = roads.setdefault(name, [cls, []])
                r[1].append(ln)
                if ROAD_WEIGHT[cls] > ROAD_WEIGHT[r[0]]:
                    r[0] = cls
        for name, (cls, parts) in roads.items():
            g = unary_union(parts)
            consider(f"road:{name}", {"name": name}, g, "road", ROAD_WEIGHT[cls], g.length)
        rep["landmarks_excluded"] = excluded
        out = list(pool.values())
        rep["landmark_pool_size"] = len(out)
        rep["automated_checks"].append("landmark candidates screened: stop targets, features holding a "
                                       "target, and every stop's secret terms")
        return out

    def _start_point(self):
        """Where the walk begins: a named street corner near circle 1 that lies outside every
        circle, inside the route's padded extent, and carries no stop's secret terms. Corners
        of two main streets rank first, then the nearest. Picked from the map data; a marker
        and a caption, never a leg."""
        rep = self.report
        stops = self.m["stops"]
        secrets = [stop_terms(st) for st in stops]
        circles = [Point(cx, cy).buffer(r + START_CLEAR_M) for cx, cy, r in self.areas]
        c1 = Point(self.areas[0][0], self.areas[0][1]).buffer(self.areas[0][2])
        pts = [p for L in self.legs for p in L["xy"]]
        for cx, cy, r in self.areas:
            pts += [(cx - r, cy - r), (cx + r, cy + r)]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        padx, pady = (max(xs) - min(xs)) * PANEL_PAD, (max(ys) - min(ys)) * PANEL_PAD
        frame = sbox(min(xs) - padx, min(ys) - pady, max(xs) + padx, max(ys) + pady)
        at_node = {}
        for wid, (refs, t) in self.ways.items():
            cls = street_class(t)
            if cls not in ("major", "minor") or t.get("highway") == "service" or not t.get("name"):
                continue
            for nid in refs:
                if nid in self.nodes:
                    at_node.setdefault(nid, {})[t["name"]] = cls
        cands = []
        for nid, names in at_node.items():
            if len(names) < 2:
                continue
            xy = self.P(*self.nodes[nid][:2])
            pt = Point(xy)
            if not frame.contains(pt) or any(c.contains(pt) for c in circles):
                continue
            if any(term_hits(n, terms) for n in names for terms in secrets):
                continue
            d = c1.distance(pt)
            if d > START_REACH_M:
                continue
            major = sum(1 for c in names.values() if c == "major")
            cands.append((-major, d, nid, sorted(names)))    # main-street corners first, then nearest
        if not cands:
            rep["errors"].append(f"start: no named street corner outside the circles within "
                                 f"{START_REACH_M / FT:.0f} ft of circle 1 inside the map frame")
            return None
        cands.sort()
        _, d, nid, names = cands[0]
        corner = " and ".join(names[:2])
        start = {"osm": f"node/{nid}", "xy": self.P(*self.nodes[nid][:2]), "names": names[:2],
                 "caption": f"Start: {corner}", "ft_from_edge": round(d / FT)}
        rep["start"] = {k: v for k, v in start.items() if k != "xy"}
        rep["automated_checks"].append("start corner outside every circle and clear of secret terms")
        return start

    def _cafe_break(self):
        """Up to three real, named places to eat or drink, a short detour off the leg that
        starts nearest halfway. A break, not a stop: no riddle, no number."""
        rep = self.report
        stops = self.m["stops"]
        lens = [LineString(L["xy"]).length for L in self.legs]
        total = sum(lens)
        # break after stop k: the stop whose walking distance from the start is nearest halfway
        to_stop = {m: sum(lens[:m - 1]) for m in range(1, len(stops))}
        k = min(to_stop, key=lambda m: abs(to_stop[m] - total / 2))
        leg = LineString(self.legs[k - 1]["xy"])    # legs[k-1] runs from stop k to stop k+1
        secrets = [stop_terms(st) for st in stops]
        circles = [Point(cx, cy).buffer(r + 10) for cx, cy, r in self.areas]
        target_refs = {st.get("target") for st in stops}
        cands = []

        def consider(ref, t, xy):
            name = t.get("name")
            if not name or ref in target_refs:
                return
            w = max([wt for (kk, vv), wt in CAFE_KINDS.items() if t.get(kk) == vv] or [0])
            if not w:
                return
            pt = Point(xy)
            if any(c.contains(pt) for c in circles):
                return                               # never inside a hunt circle
            if any(term_hits(name, terms) for terms in secrets):
                return
            cands.append({"name": name, "osm": ref, "xy": xy, "pt": pt, "weight": w,
                          "kind": next(f"{kk}={vv}" for (kk, vv) in CAFE_KINDS if t.get(kk) == vv),
                          "hours": t.get("opening_hours"), "brand": bool(t.get("brand"))})

        for nid, (lat, lon, t) in self.nodes.items():
            if t and t.get("name"):
                consider(f"node/{nid}", t, self.P(lat, lon))
        for wid, (refs, t) in self.ways.items():
            if t.get("name") and (t.get("amenity") in ("cafe", "restaurant", "ice_cream")
                                  or t.get("shop") in ("bakery", "pastry")):
                xy = _way_xy(wid, self.ways, self.nodes, self.P)
                if len(xy) >= 3:
                    c = Polygon(xy).centroid
                    consider(f"way/{wid}", t, (c.x, c.y))
        picks = []
        for detour in CAFE_DETOUR_M:
            near = []
            for c in cands:
                d = leg.distance(c["pt"])
                if d > detour:
                    continue
                along = leg.project(c["pt"]) / max(leg.length, 1.0)
                score = (c["weight"] + (0.5 if c["hours"] else 0.0) - (0.5 if c["brand"] else 0.0)
                         - d / CAFE_DETOUR_M[0] - 1.0 * max(0.0, along - 0.5)
                         - 0.03 * max(0, len(c["name"]) - 16))
                near.append((score, d, c))
            near.sort(key=lambda q: -q[0])
            for score, d, c in near:
                if all(c["pt"].distance(p["pt"]) >= CAFE_SPACING_M for p in picks):
                    picks.append(dict(c, ft_from_route=round(d / FT), score=round(score, 2)))
                if len(picks) >= CAFE_PICKS * 2:      # spares in case labels do not fit
                    break
            if picks:
                break
        rep["cafe_break"] = {"after_stop": k, "candidates": [
            {"name": p["name"], "osm": p["osm"], "url": f"https://www.openstreetmap.org/{p['osm']}",
             "kind": p["kind"], "ft_from_route": p["ft_from_route"], "opening_hours": p["hours"]}
            for p in picks]}
        if not picks:
            rep["warnings"].append(f"café break: no named café, bakery or restaurant within "
                                   f"{CAFE_DETOUR_M[-1] / FT:.0f} ft of the route after stop {k}")
        for p in picks:
            p["after_stop"] = k
        return picks

    def landmark_score(self, cand, j):
        """Rank a candidate for circle j: kind first, then size, closeness and a short name."""
        size = cand["size"]
        sz = math.log10(max(size, 1.0) / (1000.0 if cand["kind"] == "outline" else 100.0))
        d = cand["dists"].get(j, 1e9)
        return (cand["weight"] + 0.4 * max(-1.0, min(1.5, sz)) - 1.0 * d / LANDMARK_REACH_M
                - 0.03 * max(0, len(cand["name"]) - 12) - (1.0 if cand["faint"] else 0.0))

    def _element_poly(self, ref):
        kind, oid = ref.split("/")
        if kind == "way" and oid in self.ways:
            polys = _polys(lambda t: True, {oid: self.ways[oid]}, {}, self.nodes, self.P)
        elif kind == "relation" and oid in self.rels:
            rtags = self.rels[oid][1]
            polys = _polys(lambda t: t is rtags, self.ways, {oid: self.rels[oid]}, self.nodes, self.P,
                           scan_ways=False)
        else:
            return None
        return unary_union(polys) if polys else None

    # ---- route helpers

    def _crossings(self, path):
        out = []
        for k in range(1, len(path) - 1):
            v = path[k]
            w_in = self.edge_way.get(frozenset((path[k - 1], v)))
            w_out = self.edge_way.get(frozenset((v, path[k + 1])))
            for wid, (refs, t) in self.ways.items():
                if t.get("highway") not in MAJOR or v not in refs:
                    continue
                if wid in (w_in, w_out):
                    continue
                ntag = self.nodes[v][2]
                kind = ntag.get("crossing") or (
                    "marked" if ntag.get("highway") in ("crossing", "traffic_signals") else None)
                for wx in (w_in, w_out):
                    if wx and self.ways[wx][1].get("footway") == "crossing":
                        kind = kind or self.ways[wx][1].get("crossing")
                control = ("controlled" if kind in ("traffic_signals", "zebra", "marked", "uncontrolled")
                           else "unmarked" if kind in ("unmarked", "no") else "unknown")
                out.append({"road": t.get("name") or t.get("ref") or t["highway"],
                            "osm_node": f"node/{v}", "crossing_tag": kind, "control": control})
                break
        # crossings drawn as separate footway=crossing ways
        for a, b in zip(path, path[1:]):
            wid = self.edge_way.get(frozenset((a, b)))
            t = self.ways[wid][1] if wid else {}
            if t.get("footway") == "crossing":
                kind = t.get("crossing")
                control = ("controlled" if kind in ("traffic_signals", "zebra", "marked", "uncontrolled")
                           else "unmarked" if kind in ("unmarked", "no") else "unknown")
                rec = {"road": "crossing way", "osm_way": f"way/{wid}",
                       "crossing_tag": kind, "control": control}
                if rec not in out:
                    out.append(rec)
        return out

    def _areas(self, stops, slug):
        rep = self.report
        areas = []
        for i, (st, (tx, ty)) in enumerate(zip(stops, self.targets), 1):
            g = self.group[i - 1]
            if g != i - 1:                       # member of a shared circle: reuse it
                areas.append(areas[g])
                if math.dist(areas[g][:2], (tx, ty)) >= areas[g][2]:
                    rep["errors"].append(f"area {i}: target outside its shared circle")
                continue
            members = [k for k in range(len(stops)) if self.group[k] == i - 1]
            if "area_radius_m" in st:
                rep["errors"].append(f"area {i}: `area_radius_m` is retired; give the radius in "
                                     "feet as `area_radius_ft`")
            if "area_radius_ft" in st:
                r = float(st["area_radius_ft"]) * FT
            else:
                r = DEFAULT_AREA_RADIUS_M
            if r < MIN_AREA_RADIUS_M - 1e-6:
                rep["errors"].append(f"area {i}: radius {r / FT:.0f} ft ({r:.0f} m) below the "
                                     f"100 ft ({MIN_AREA_RADIUS_M:.1f} m) floor")
            seed = int(hashlib.sha256(f"{slug}:{i}".encode()).hexdigest(), 16)
            frac = MIN_CENTRE_OFFSET + (seed % 1000) / 1000 * (MAX_CENTRE_OFFSET - MIN_CENTRE_OFFSET)
            others = [t for k, t in enumerate(self.targets) if k not in members]
            if len(members) > 1:
                # one circle holding several targets: centred near their midpoint, every target
                # well inside, none at the centre
                pts = [self.targets[k] for k in members]
                mx, my = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
                best = None
                for t in (0.0, 0.1, 0.2, 0.3, 0.4, MAX_CENTRE_OFFSET):
                    for k in range(16):
                        ang = math.radians((seed >> 12) % 360 + k * 22.5)
                        cx, cy = mx + math.cos(ang) * t * r, my + math.sin(ang) * t * r
                        dists = [math.dist((cx, cy), p) for p in pts]
                        if max(dists) > 0.85 * r or min(dists) < MIN_CENTRE_OFFSET * r:
                            continue
                        score = min(math.dist((cx, cy), o) for o in others) if others else 0
                        if best is None or score > best[0] + 1e-6:
                            best = (score, cx, cy)
                if best is None:
                    rep["errors"].append(f"area {i}: shared circle of radius {r / FT:.0f} ft cannot hold "
                                         f"stops {', '.join(str(k + 1) for k in members)} well inside it")
                    best = (0, mx, my)
                areas.append((best[1], best[2], r))
                continue
            best = None
            for k in range(16):
                ang = math.radians((seed >> 12) % 360 + k * 22.5)
                cx, cy = tx + math.cos(ang) * frac * r, ty + math.sin(ang) * frac * r
                score = min(math.dist((cx, cy), o) for o in others)
                if best is None or score > best[0] + 1e-6:
                    best = (score, cx, cy)
            _, cx, cy = best
            areas.append((cx, cy, r))
            off = math.dist((cx, cy), (tx, ty))
            if off >= r:
                rep["errors"].append(f"area {i}: target outside its area")
        for a in range(len(areas)):
            for b in range(a + 1, len(areas)):
                if self.group[a] == self.group[b]:
                    continue
                d = math.dist(areas[a][:2], areas[b][:2])
                if d < areas[a][2] + areas[b][2]:
                    rep["errors"].append(f"areas {a+1} and {b+1} overlap (centres "
                                         + (f"{d / FT:.0f} ft" if self.units == "imperial" else f"{d:.0f} m")
                                         + " apart); "
                                         "reduce radius or choose distinct stops")
        return areas

    # ---- layout

    def layout(self, box, text_width, furniture_h=0):
        """Fit to box (x0, y0, w, h) in points. Returns a Layout."""
        return Layout(self, box, text_width)

    # ---- panel planning: one map page, or two for long routes

    def _grown_area(self, g, r_new):
        """Circle g scaled about its target(s) to radius r_new: the target keeps the same
        relative off-centre position, so a bigger circle gives nothing away."""
        cx, cy, r = self.areas[g]
        members = [k for k in range(len(self.areas)) if self.group[k] == g]
        pts = [self.targets[k] for k in members]
        ox, oy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        f = r_new / r
        return (ox + (cx - ox) * f, oy + (cy - oy) * f, r_new)

    def _panel_scale(self, stops, carry, w, h, radii=None, carry_area=None):
        """Scale the panel would print at (filling the plate) and the scale legibility needs.
        stops: 0-based stop indices with full circles; carry: 0-based stop shown as a disc only;
        radii: {leader: grown radius in metres} for this page."""
        radii = radii or {}
        area = lambda k: (self._grown_area(self.group[k], radii[self.group[k]])
                          if self.group[k] in radii else self.areas[k])
        keep = set(stops) | ({carry} if carry is not None else set())
        pts = []
        for L in self.legs:
            if L["from"] - 1 in keep and L["to"] - 1 in keep:
                pts += L["xy"]
        for k in stops:
            cx, cy, r = area(k)
            pts += [(cx - r, cy - r), (cx + r, cy + r)]
        if carry is not None:          # carried-in stop: its full circle, as on its own page
            cx, cy, r = carry_area or self.areas[carry]
            pts += [(cx - r, cy - r), (cx + r, cy + r)]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        cw, ch = (max(xs) - min(xs)) * (1 + 2 * PANEL_PAD), (max(ys) - min(ys)) * (1 + 2 * PANEL_PAD)
        s_fit = min(w / max(cw, 1.0), h / max(ch, 1.0))
        needs = []                       # (scale needed, reason, fix, kind, leader) per constraint
        leaders = sorted({self.group[k] for k in stops})
        for g in leaders:
            n = sum(1 for k in stops if self.group[k] == g)
            r = area(g)[2]
            need_pt = max(2 * DISC_R, ((n - 1) * (2 * DISC_R + 3)) / 2 + DISC_R + 4)
            needs.append((need_pt / r, f"circle {g + 1} is {r / FT:.0f} ft",
                          f"needs {need_pt:.1f} pt radius on paper", "circle", g, need_pt))
        for a in leaders:
            for b in leaders:
                if b <= a:
                    continue
                ca, cb = area(a), area(b)
                gap = math.dist(ca[:2], cb[:2]) - ca[2] - cb[2]
                if gap > 0:
                    needs.append((GAP_PT / gap, f"circles {a + 1} and {b + 1} are {gap / FT:.0f} ft apart",
                                  f"need {GAP_PT:.0f} pt between them on paper", "gap", (a, b), GAP_PT))
                else:
                    needs.append((1e9, f"circles {a + 1} and {b + 1} overlap",
                                  "circles must stay apart", "overlap", (a, b), 0))
        # a grown circle must not swallow another stop's target
        for g in radii:
            cx, cy, r = self._grown_area(g, radii[g])
            for k, t in enumerate(self.targets):
                if self.group[k] != g and math.dist((cx, cy), t) < r:
                    needs.append((1e9, f"circle {g + 1} grown to {r / FT:.0f} ft takes in stop {k + 1}",
                                  "a circle holds only its own targets", "swallow", g, 0))
        s_req = max(n[0] for n in needs) if needs else 0.0
        return s_fit, s_req, needs

    def _fit_panel(self, stops, carry, w, h, carry_area=None):
        """Panel at its fitted scale, growing circles that would print too small, up to
        CIRCLE_MAX_FT. Returns the panel dict; feasible when s_fit >= s_req."""
        radii = {}
        cap = CIRCLE_MAX_FT * FT
        for _ in range(6):
            s_fit, s_req, needs = self._panel_scale(stops, carry, w, h, radii, carry_area)
            if s_fit >= s_req:
                break
            grew = False
            for need, _, _, kind, g, need_pt in needs:
                if kind != "circle" or need <= s_fit:
                    continue
                r_now = radii.get(g, self.areas[g][2])
                r_new = min(cap, need_pt / s_fit * 1.03)
                if r_new > r_now + 0.01:
                    radii[g] = r_new
                    grew = True
            if not grew:
                break
        growth = sum(radii[g] / self.areas[g][2] - 1 for g in radii)
        return {"stops": list(stops), "carry": carry, "s_fit": s_fit, "s_req": s_req,
                "needs": needs, "radii": radii, "growth": growth, "carry_area": carry_area}

    def plan_panels(self, w, h):
        """Decide the map pages before drawing anything: the fewest pages (up to MAX_MAP_PAGES)
        on which every circle reads, circles growing up to CIRCLE_MAX_FT where a page must print
        small; then the least growth. On failure records every violated constraint with its fix."""
        import itertools
        n = len(self.areas)
        rep = self.report
        allstops = list(range(n))
        if self.m.get("frame"):
            plan = [{"stops": allstops, "carry": None, "radii": {}}]
            rep["panel_plan"] = {"pages": 1, "why": "locked frame", "panels": [{"stops": [1, n]}]}
            return plan
        cut_ok = [k for k in range(1, n) if self.group[k] == k]   # never split a shared circle
        plans = []
        for npg in range(1, MAX_MAP_PAGES + 1):
            for cuts in itertools.combinations(cut_ok, npg - 1):
                bounds = [0, *cuts, n]
                plan = []
                for a, c in zip(bounds, bounds[1:]):
                    ca = None
                    if a:                         # carried-in circle at its previous page's size
                        g = self.group[a - 1]
                        prev = plan[-1]["radii"]
                        ca = self._grown_area(g, prev[g]) if g in prev else self.areas[a - 1]
                    plan.append(self._fit_panel(list(range(a, c)), a - 1 if a else None, w, h, ca))
                margin = min(p["s_fit"] / p["s_req"] if p["s_req"] else 9.0 for p in plan)
                plans.append((npg, margin, sum(p["growth"] for p in plan), plan))
        ok = [x for x in plans if x[1] >= 1.0]
        if ok:
            # circles keep their interview size whenever some plan allows it; growth is the
            # fallback for long legs, never a way to save a page
            npg, margin, growth, plan = min(ok, key=lambda x: (x[2] > 1e-9, x[0], x[2], -x[1]))
        else:
            npg, margin, growth, plan = max(plans, key=lambda x: (x[1], -x[0]))
        rep["panel_plan"] = {"pages": len(plan), "panels": [
            {"stops": [p["stops"][0] + 1, p["stops"][-1] + 1],
             "carry_in": (p["carry"] + 1) if p.get("carry") is not None else None,
             "scale_pt_per_m": round(p["s_fit"], 3), "needed_pt_per_m": round(p["s_req"], 3),
             "circles_grown_ft": {g + 1: round(r / FT) for g, r in sorted(p["radii"].items())}}
            for p in plan]}
        for p in plan:
            for g, r in sorted(p["radii"].items()):
                rep["warnings"].append(f"circle {g + 1} grown from {self.areas[g][2] / FT:.0f} ft to "
                                       f"{r / FT:.0f} ft so it reads at this page's scale")
        if any(p["radii"] for p in plan):
            # pick the café break and the start again against the circles as they will print
            orig = self.areas
            grown = list(orig)
            for p in plan:
                for k in range(n):
                    if self.group[k] in p["radii"] and k in p["stops"]:
                        grown[k] = self._grown_area(self.group[k], p["radii"][self.group[k]])
            self.areas = grown
            try:
                if self.m.get("cafe_break"):
                    self.cafes = self._cafe_break()
                before = self.start
                self.start = self._start_point()
                if before and self.start and before["osm"] != self.start["osm"]:
                    rep["warnings"].append(f"start moved to {self.start['caption'][7:]} once circles grew; "
                                           f"the cold-solver packet must be printed again")
            finally:
                self.areas = orig
        if margin >= 1.0:
            return plan
        # one consolidated diagnosis: every constraint that the best plan cannot meet
        for pg, p in enumerate(plan, 1):
            a, b = p["stops"][0] + 1, p["stops"][-1] + 1
            span = f"stop {a}" if a == b else f"stops {a}–{b}"
            where = f"page {pg} ({span})" if len(plan) > 1 else "the map"
            for need, what, why, kind, g, _ in sorted(p["needs"], key=lambda x: -x[0]):
                if need > p["s_fit"]:
                    fix = ""
                    if kind == "circle":
                        fix = (f"; even at the {CIRCLE_MAX_FT} ft cap it needs at least "
                               f"{math.ceil(need / p['s_fit'] * float(what.split()[3]) / 10) * 10:.0f} ft; "
                               f"shorten the legs around it or split the walk")
                    elif kind == "gap":
                        fix = "; consider one shared circle (shares_area_with) for stops this close"
                    rep["errors"].append(f"plan: {where} prints at {p['s_fit']:.2f} pt/m but {what} and "
                                         f"{why}{fix}")
        return plan

    def panel(self, p):
        """A copy of the model restricted to one page's stops (plus the carried-in stop)."""
        import copy
        keep = ([p["carry"]] if p.get("carry") is not None else []) + list(p["stops"])
        sub = copy.copy(self)
        local = {g: i for i, g in enumerate(keep)}
        sub.m = dict(self.m, stops=[self.m["stops"][k] for k in keep])
        radii = p.get("radii", {})
        sub.areas = [p["carry_area"] if (k == p.get("carry") and p.get("carry_area")) else
                     self._grown_area(self.group[k], radii[self.group[k]]) if self.group[k] in radii
                     else self.areas[k] for k in keep]
        sub.targets = [self.targets[k] for k in keep]
        sub.group = [local.get(self.group[k], i) for i, k in enumerate(keep)]
        sub.numbers = [k + 1 for k in keep]
        sub.ghosts = {0} if p.get("carry") is not None else set()
        sub.legs = [dict(L, **{"from": local[L["from"] - 1] + 1, "to": local[L["to"] - 1] + 1})
                    for L in self.legs if L["from"] - 1 in local and L["to"] - 1 in local]
        # the café break sits beside the leg after its stop: it goes on the page drawing that leg
        sub.cafes = [c for c in self.cafes if (c["after_stop"] - 1) in local and c["after_stop"] in local]
        sub.start = self.start if 0 in local and 0 not in sub.ghosts else None
        sub.landmark_pool = [dict(c, dists={local[g]: d for g, d in c["dists"].items() if g in local})
                             for c in self.landmark_pool]
        sub.report = {"errors": [], "warnings": [], "automated_checks": [], "labels": self.report.get("labels")}
        for key in ("labels_placed", "labels_dropped", "labels_suppressed"):
            if key in self.report:
                sub.report[key] = []
        return sub


def layout_extent(model, box):
    """Ground extent (metres) and print scale (points per metre) a page's map will use."""
    x0, y0, w, h = box
    pts = [p for L in model.legs for p in L["xy"]]
    for k, (cx, cy, r) in enumerate(model.areas):   # carried-in stop: full circle too
        pts += [(cx - r, cy - r), (cx + r, cy + r)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    pad = model.m.get("padding", PANEL_PAD)
    ex0, ex1, ey0, ey1 = min(xs), max(xs), min(ys), max(ys)
    dx, dy = ex1 - ex0, ey1 - ey0
    ex0 -= dx * pad; ex1 += dx * pad; ey0 -= dy * pad; ey1 += dy * pad
    # expand to the box aspect ratio
    frame = model.m.get("frame")
    if frame:   # author-locked framing: [min_lon, min_lat, max_lon, max_lat]
        lo0, la0, lo1, la1 = frame["bbox"]
        ex0, ey0 = model.P(la0, lo0)
        ex1, ey1 = model.P(la1, lo1)
    aspect = w / h
    cw, ch = ex1 - ex0, ey1 - ey0
    if cw / ch < aspect:
        extra = ch * aspect - cw
        ex0 -= extra / 2; ex1 += extra / 2
    else:
        extra = cw / aspect - ch
        ey0 -= extra / 2; ey1 += extra / 2
    return ex0, ey0, ex1, ey1, w / (ex1 - ex0)


SCALE_NICE = {"imperial": [50, 100, 200, 250, 300, 400, 500, 1000, 1500, 2000],
              "metric": [10, 20, 25, 50, 100, 150, 200, 250, 500, 1000]}
BAR_MIN_PT, BAR_MAX_PT = 28, 120


def shared_scale_value(scales, w, units):
    """One scale-bar value for every page, if a bar of that value reads on all of them
    (between BAR_MIN_PT and BAR_MAX_PT long); else None and each page picks its own."""
    unit = FT if units == "imperial" else 1.0
    target = w * 0.22
    best = None
    for v in SCALE_NICE["imperial" if units == "imperial" else "metric"]:
        lens = [v * unit * s for s in scales]
        if min(lens) < BAR_MIN_PT or max(lens) > BAR_MAX_PT:
            continue
        err = max(abs(math.log(L / target)) for L in lens)
        if best is None or err < best[0]:
            best = (err, v)
    return best[1] if best else None


class Layout:
    def __init__(self, model, box, text_width):
        self.mm = model
        self.box = box
        self.tw = text_width
        x0, y0, w, h = box
        ex0, ey0, ex1, ey1, self.s = layout_extent(model, box)
        frame = model.m.get("frame")
        if frame:
            fb = sbox(ex0, ey0, ex1, ey1)
            for j, (cx, cy, r) in enumerate(model.areas, 1):
                if model.group[j - 1] != j - 1 or (j - 1) in model.ghosts:
                    continue
                if not fb.contains(Point(cx, cy).buffer(r)):
                    model.report["errors"].append(f"frame: circle {j} falls outside the locked frame")
        self.ext = (ex0, ey0, ex1, ey1)
        self.extent_m = (round(ex1 - ex0), round(ey1 - ey0))
        self.clip_m = sbox(ex0, ey0, ex1, ey1)
        self.plate = sbox(x0, y0, x0 + w, y0 + h)
        rep = model.report
        rep["scale"] = {"points_per_metre": round(self.s, 4),
                        "extent_m": self.extent_m,
                        "ratio_at_print": f"1:{round(1 / (self.s / 72 * 0.0254)):,}"}
        self._geometry()
        if not model.auto_landmarks:
            self._visible_landmark_check()
        self._furniture()
        self._labels()

    def T(self, x, y):
        x0, y0, _, _ = self.box
        return (x0 + (x - self.ext[0]) * self.s, y0 + (y - self.ext[1]) * self.s)

    def Tg(self, g):
        x0, y0, _, _ = self.box
        g = affinity.translate(g, -self.ext[0], -self.ext[1])
        g = affinity.scale(g, self.s, self.s, origin=(0, 0))
        return affinity.translate(g, x0, y0)

    def _clip(self, geoms, simplify=0.0):
        out = []
        for g in geoms:
            if not g.intersects(self.clip_m):
                continue
            gg = g.intersection(self.clip_m)
            if simplify:
                gg = gg.simplify(simplify, preserve_topology=True)
            if not gg.is_empty:
                out.append(self.Tg(gg))
        return out

    def _visible_landmark_check(self):
        """A landmark only counts for a circle if the part of it within reach is on the map."""
        mm, rep = self.mm, self.mm.report
        inner = self.clip_m.buffer(-6 / self.s)        # keep clear of the frame edge
        for j, (cx, cy, r) in enumerate(mm.areas, 1):
            if mm.group[j - 1] != j - 1 or (j - 1) in mm.ghosts:
                continue
            circ = Point(cx, cy).buffer(r, 48)
            seen = [(lm["poly"].intersection(inner).distance(circ), lm["label"]) for lm in mm.landmarks
                    if not lm["poly"].intersection(inner).is_empty]
            best = min(seen) if seen else None
            if not best or best[0] > LANDMARK_REACH_M:
                hidden = [lm["label"].replace("|", " ") for lm in mm.landmarks
                          if lm["poly"].distance(circ) <= LANDMARK_REACH_M
                          and (lm["poly"].intersection(inner).is_empty
                               or lm["poly"].intersection(inner).distance(circ) > LANDMARK_REACH_M)]
                if hidden:
                    rep["errors"].append(f"landmark: circle {j}'s landmark {', '.join(hidden)} falls "
                                         f"outside the map frame; choose one that is on the map")

    def _geometry(self):
        mm = self.mm
        self.water = self._clip(mm.water, 0.5)
        self.streets = []
        anchor_names = {lm["name"] for lm in mm.landmarks if lm["kind"] == "road"}
        self.anchor_roads, self.circle_detail = [], []
        circles_m = [Point(cx, cy).buffer(r, 48) for k, (cx, cy, r) in enumerate(mm.areas)
                     if mm.group[k] == k]
        for cls, ln, name, bridge, wid in mm.streets:
            for cm in circles_m:              # full street detail inside every circle
                if ln.intersects(cm):
                    self.circle_detail.append((cls, self.Tg(ln.intersection(cm))))
            if name in anchor_names and ln.intersects(self.clip_m):
                self.anchor_roads.append(self.Tg(ln.intersection(self.clip_m)))
                continue
            if not (cls == "major" or wid in mm.route_ways):
                continue
            if ln.intersects(self.clip_m):
                self.streets.append((cls, self.Tg(ln.intersection(self.clip_m)), name, bridge))
        self.landmarks = []
        for lm in mm.landmarks:
            g = lm["poly"]
            if g.intersects(self.clip_m):
                self.landmarks.append(dict(lm, shape=self.Tg(g.intersection(self.clip_m))))
        # route clipped outside hunt areas, so no line ends on a target
        circles = [Point(*self.T(cx, cy)).buffer(r * self.s, 48) for cx, cy, r in mm.areas]
        # a carried-in stop keeps its circle (same ground size as on its own page); a circle
        # printing smaller than its number disc still reserves the disc
        self.area_shapes = [Point(*self.T(cx, cy)).buffer(max(r * self.s, CARRY_MIN_PT), 48)
                            if k in mm.ghosts else c
                            for k, ((cx, cy, r), c) in enumerate(zip(mm.areas, circles))]
        self.circle_centres = [self.T(cx, cy) for cx, cy, _ in mm.areas]
        self.marker_r = 7.6
        # number discs: one at the centre, or side by side in walking order for a shared circle
        self.area_centres = []
        for k, (cx, cy) in enumerate(self.circle_centres):
            mem = [j for j in range(len(mm.areas)) if mm.group[j] == mm.group[k]]
            off = (mem.index(k) - (len(mem) - 1) / 2) * (2 * self.marker_r + 3)
            self.area_centres.append((cx + off, cy))
        route = unary_union([LineString([self.T(*p) for p in L["xy"]]) for L in mm.legs])
        self.route_full = route
        self.route = route.difference(unary_union(circles))
        self.marker_r = 7.6
        self.markers = [Point(c).buffer(self.marker_r + 1.0, 24) for c in self.area_centres]

    def _furniture(self):
        x0, y0, w, h = self.box
        # scale bar: a round length near 22% of the plate width
        fixed = getattr(self.mm, "scale_value", None)     # shared across pages when set
        if self.mm.units == "imperial":
            target = w * 0.22 / self.s / FT
            nice = SCALE_NICE["imperial"]
            L = fixed or min(nice, key=lambda n: abs(n - target))
            self.scale_text, self.scale_len = f"{L} ft", L * FT * self.s
        else:
            target = w * 0.22 / self.s
            nice = SCALE_NICE["metric"]
            L = fixed or min(nice, key=lambda n: abs(n - target))
            self.scale_text, self.scale_len = f"{L} m", L * self.s
        # attribution: fixed, bottom right (licence requirement)
        self.attrib = self.mm.manifest.get("attribution", "© OpenStreetMap contributors")
        self.attrib_text = f"Map data {self.attrib}, ODbL · openstreetmap.org/copyright"
        aw = self.tw(self.attrib_text, "Body", FURNITURE_PT)
        self.attrib_rect = sbox(x0 + w - aw - 9, y0 + 2, x0 + w - 2, y0 + 12)
        # scale bar and north arrow take the first corner clear of circles, route and landmarks
        block = list(self.area_shapes)
        if not self.route.is_empty:
            block.append(self.route.buffer(2))
        block += [lm["shape"].buffer(6) for lm in self.landmarks
                  if lm["kind"] == "road" or not lm.get("faint")]
        taken = [self.attrib_rect]
        L = self.scale_len

        def free(r):
            return not any(r.intersects(o) for o in block + taken)

        # scale bar and north arrow travel together as one group, side by side, in a corner;
        # the arrow sits on the border side (left in left corners, right in right corners)
        layouts = [("side by side", L + 54, 44)]
        streets_u = unary_union([g for _, g, _, _ in self.streets] + list(self.anchor_roads)) \
            if self.streets else None
        rep = self.mm.report
        pick = None
        best_loose = None
        sb = streets_u.buffer(2) if streets_u is not None else None
        for strict in (True, False):
            if not strict and best_loose:
                pick = best_loose[1]
                break
            for arr, gw, gh in layouts:
                corners = [("bottom left", x0 + 5, y0 + 5), ("top left", x0 + 5, y0 + h - gh - 5),
                           ("top right", x0 + w - gw - 5, y0 + h - gh - 5),
                           ("bottom right", x0 + w - gw - 5, y0 + 16)]
                for name, gx0, gy in corners:
                    inward = 1 if "left" in name else -1
                    for slide in range(0, FURNITURE_SLIDE + 1, 4):
                        gx = gx0 + inward * slide
                        gr = sbox(gx, gy, gx + gw, gy + gh)
                        if not free(gr):
                            continue
                        overlap = gr.intersection(sb).area if sb is not None else 0.0
                        if overlap == 0.0:
                            pick = (name, arr, gx, gy, gw, gh)
                            break
                        if best_loose is None or overlap < best_loose[0]:
                            best_loose = (overlap, (name, arr, gx, gy, gw, gh))
                    if pick:
                        break
                if pick:
                    break
            if pick:
                break
        if not pick:
            arr, gw, gh = layouts[0]
            pick = ("bottom left", arr, x0 + 5, y0 + 5, gw, gh)
            rep["warnings"].append("furniture: no clear corner for the scale bar and north arrow")
        name, arr, gx, gy, gw, gh = pick
        # a page printed at a different scale from the one before says so under its bar
        self.scale_note = None
        prev = getattr(self.mm, "prev_scale", None)
        if prev and abs(math.log(self.s / prev[0])) > math.log(1 + SCALE_NOTE_RATIO):
            self.scale_note = f"Zoomed {'out' if self.s < prev[0] else 'in'} from page {prev[1]}"
        note_h = 8 if self.scale_note else 0
        left = "left" in name           # the arrow always sits on the border side of the group
        top = "top" in name             # the scale bar always sits nearest the top/bottom border
        sx = gx + 29 if left else gx + 5
        sy = gy + gh - 14 if top else gy + 6 + note_h
        nx, ny = (gx + 11, gy + 24) if left else (gx + gw - 11, gy + 24)
        self.scale_at = (sx, sy)
        note_w = self.tw(self.scale_note, "Body-Italic", FURNITURE_PT) if self.scale_note else 0
        self.scale_rect = sbox(sx - 3, sy - 4 - note_h, sx + max(L + 27, note_w + 3), sy + 11)
        self.north, self.north_rect = (nx, ny), sbox(nx - 10, ny - 22, nx + 10, ny + 20)
        nname = f"{name}, {arr}"
        rep["furniture"] = {"scale_and_north": nname}
        self.furniture = [self.scale_rect, self.north_rect, self.attrib_rect]

    # ---- label placement

    def _box_poly(self, cx, cy, bw, bh, ang=0.0):
        p = sbox(cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
        return affinity.rotate(p, ang, origin=(cx, cy)) if ang else p

    def _text_w(self, s, font, size, tracking):
        return self.tw(s, font, size) + tracking * max(0, len(s) - 1)

    def _clear(self, poly, kind, own_area=None):
        cache = self.__dict__.setdefault("_clear_cache", {})
        if "inner" not in cache:
            cache["inner"] = self.plate.buffer(-3)
            cache["route"] = self.route.buffer(1.4) if not self.route.is_empty else Point(-1e9, -1e9)
            from shapely.prepared import prep
            cache["route_p"] = prep(cache["route"])
        if not cache["inner"].contains(poly):
            return False
        if cache["route_p"].intersects(poly):
            return False
        placed = cache.setdefault("placed", [])
        while len(placed) < len(self.placed_polys):
            placed.append(self.placed_polys[len(placed)].buffer(1.4))
        obstacles = list(self.furniture) + self.markers + placed
        own = self.mm.group[own_area] if own_area is not None else None
        obstacles += [a for k, a in enumerate(self.area_shapes) if self.mm.group[k] != own]
        return not any(poly.intersects(o) for o in obstacles)

    def _labels(self):
        mm, rep = self.mm, self.mm.report
        stops = mm.m["stops"]
        secrets = [(i, stop_terms(st)) for i, st in enumerate(stops, 1)]
        suppress_extra = mm.m.get("labels", {}).get("suppress", [])
        self.placed, self.placed_polys = [], []

        def secret_hit(name):
            for i, terms in secrets:
                h = term_hits(name, terms)
                if h:
                    return f"matches secret term '{h[0]}' for stop {i}"
            if term_hits(name, suppress_extra):
                return "suppressed by spec"
            return None

        self._place_required(secret_hit)
        # 2. river names along the centreline
        rivers = {}
        for name, ln in mm.rivers:
            if name and ln.intersects(self.clip_m):
                rivers.setdefault(name, []).append(self.Tg(ln.intersection(self.clip_m)))
        for name, parts in rivers.items():
            why = secret_hit(name)
            if why:
                rep["labels"]["suppressed"].append({"text": name, "reason": why})
                continue
            self._line_label(name.upper(), parts, "Body-Italic", FEATURE_LABEL_PT, 1.0, "water", name)
        # 3. street names, major first, longest first
        rank = {"major": 0, "minor": 1, "service": 3, "path": 4}
        byname = {}
        for cls, ln, name, bridge in self.streets:
            if not name or cls in ("service",):
                continue
            byname.setdefault(name, [cls, []])
            byname[name][1].append(ln)
            if rank[cls] < rank[byname[name][0]]:
                byname[name][0] = cls
        order = sorted(byname.items(), key=lambda kv: (rank[kv[1][0]], -sum(g.length for g in kv[1][1])))
        for name, (cls, parts) in order:
            if mm.street_label_list is not None and name not in mm.street_label_list:
                continue
            if any(lm["kind"] == "road" and lm["name"] == name for lm in mm.landmarks + self.landmarks):
                continue
            why = secret_hit(name)
            if why:
                rep["labels"]["suppressed"].append({"text": name, "reason": why})
                continue
            self._line_label(name.upper(), parts, "Body", STREET_LABEL_PT, 0.5, "street", name)
        rep["labels"]["placed"] = [{"kind": p["kind"], "text": " / ".join(p["lines"]),
                                    "size_pt": p["size"]} for p in self.placed]
        # final check: every placed label clear of every other and inside the plate
        for a in range(len(self.placed_polys)):
            for b in range(a + 1, len(self.placed_polys)):
                if self.placed_polys[a].intersects(self.placed_polys[b]):
                    rep["errors"].append("label: collision survived placement "
                                         f"({self.placed[a]['lines'][0]} / {self.placed[b]['lines'][0]})")
        if any(p["size"] < MIN_LABEL_PT for p in self.placed):
            rep["errors"].append("label: type below floor")
        rep["automated_checks"] += ["labels placed without collision against labels, markers, route, "
                                    "areas, furniture and plate edge",
                                    f"label type floor {MIN_LABEL_PT} pt; no shrinking",
                                    "geographic names matching secret terms suppressed before placement"]

    # ---- required labels: stop names and landmarks, placed together

    def _zone_options(self, i):
        """Stop-name positions for stop i (1-based), best first: floated on the rim, then beside."""
        mm = self.mm
        st = mm.m["stops"][i - 1]
        (cx, cy), shape = self.circle_centres[i - 1], self.area_shapes[i - 1]
        lines = st["zone"].split("|")
        size, tr, lead = ZONE_LABEL_PT, 0.7, ZONE_LABEL_PT + 1.6
        bw = max(self._text_w(l, "Body", size, tr) for l in lines) + 3
        bh = lead * len(lines) + 1.5
        r = shape.bounds[2] - cx
        marker = unary_union([Point(self.area_centres[j]).buffer(self.marker_r + 1.5)
                              for j in range(len(mm.areas)) if mm.group[j] == mm.group[i - 1]])
        members = [j for j in range(len(mm.areas)) if mm.group[j] == mm.group[i - 1]]
        own_disc = Point(self.area_centres[i - 1])
        other_discs = [Point(self.area_centres[j]) for j in members if j != i - 1]
        out = []

        def own_side(poly):
            """In a shared circle a stop's name must sit nearest its own number."""
            d = poly.distance(own_disc)
            return all(d < poly.distance(o) - 1.0 for o in other_discs)
        rec0 = {"kind": "zone", "stop": i, "lines": lines, "size": size, "tracking": tr, "lead": lead,
                "angle": 0, "font": "Body"}
        # first choice: float across the circle's rim, partly inside, clear of the number.
        # Top of the circle first, then round both sides, then underneath.
        rim = [90, 60, 120, 30, 150, 0, 180, 330, 210, 300, 240, 270]
        for k in (0.0, 0.3, 0.6):
            for a in rim:
                dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
                ext = abs(dx) * bw / 2 + abs(dy) * bh / 2
                px, py = cx + dx * (r + ext * k), cy + dy * (r + ext * k)
                poly = self._box_poly(px, py, bw, bh)
                if poly.intersects(marker) or not poly.intersects(shape) or not own_side(poly):
                    continue
                if self._clear(poly, "zone", own_area=i - 1):
                    out.append({"poly": poly, "cost": 0.02 * len(out),
                                "rec": dict(rec0, x=px, y=py, floated=True)})
        pref = [0, 180, 30, 150, 330, 210, 60, 120, 300, 240, 90, 270]
        for gap in (3, 8, 15, 24):
            for a in pref:
                dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
                ext = abs(dx) * bw / 2 + abs(dy) * bh / 2
                px, py = cx + dx * (r + gap + ext), cy + dy * (r + gap + ext)
                poly = self._box_poly(px, py, bw, bh)
                own = poly.distance(Point(cx, cy))
                nearer = any(poly.distance(Point(o)) < own + 4
                             for k, o in enumerate(self.circle_centres) if mm.group[k] != mm.group[i - 1])
                if not nearer and own_side(poly) and self._clear(poly, "zone"):
                    out.append({"poly": poly, "cost": 1.0 + 0.02 * len(out), "rec": dict(rec0, x=px, y=py)})
        return out

    def _point_options(self, x, y, text, kind):
        """Label positions around a point symbol, best first: right, left, above, below, diagonals."""
        size, tr = STREET_LABEL_PT, 0.3
        lead = size + 1.4
        lines = [text]
        bw = self._text_w(text, "Body", size, tr) + 3
        bh = lead + 1.5
        out = []
        for gap in (2.5, 6):
            for a in (0, 180, 90, 270, 30, 150, 330, 210):
                dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
                ext = abs(dx) * bw / 2 + abs(dy) * bh / 2
                px, py = x + dx * (CAFE_R + gap + ext), y + dy * (CAFE_R + gap + ext)
                poly = self._box_poly(px, py, bw, bh)
                if self._clear(poly, "landmark"):
                    out.append({"poly": poly, "cost": 0.02 * len(out),
                                "rec": {"kind": kind, "lines": lines, "x": px, "y": py, "size": size,
                                        "tracking": tr, "lead": lead, "angle": 0, "font": "Body-Italic"}})
        return out

    def _outline_options(self, lm, others):
        """Label positions for an outline landmark: inside it, else just beside it (never across water)."""
        lines = lm["label"].split("|")
        size, tr, lead = STREET_LABEL_PT, 0.6, STREET_LABEL_PT + 1.4
        bw = max(self._text_w(l, "Body", size, tr) for l in lines) + 3
        bh = lead * len(lines) + 1.5
        shp = lm["shape"]
        c0 = shp.representative_point()
        cands = [(c0.x, c0.y, True)]
        minx, miny, maxx, maxy = shp.bounds
        gx = minx
        while gx <= maxx:            # further inside positions, nearest the middle first
            gy = miny
            while gy <= maxy:
                if shp.contains(Point(gx, gy)):
                    cands.append((gx, gy, True))
                gy += 4
            gx += 4
        mid = Point((minx + maxx) / 2, (miny + maxy) / 2)
        cands = [cands[0]] + sorted(cands[1:], key=lambda q: Point(q[0], q[1]).distance(mid))
        for gap in (2, 6, 12):
            for a in (0, 180, 90, 270, 30, 150, 330, 210):
                dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
                hx, hy = (maxx - minx) / 2, (maxy - miny) / 2
                ex = abs(dx) * (hx + bw / 2) + abs(dy) * (hy + bh / 2)
                cx0, cy0 = (minx + maxx) / 2, (miny + maxy) / 2
                cands.append((cx0 + dx * (ex + gap), cy0 + dy * (ex + gap), False))
        water_u = unary_union(self.water) if self.water else None
        out = []
        for px, py, inside in cands:
            poly = self._box_poly(px, py, bw, bh)
            if inside and not shp.buffer(1).contains(poly):
                continue
            if any(poly.intersects(o) for o in others):
                continue
            if not inside and (poly.intersects(shp) or poly.distance(shp) > 8):
                continue
            if not inside and water_u is not None:
                from shapely.ops import nearest_points
                a_pt, b_pt = nearest_points(poly, shp)
                if LineString([a_pt, b_pt]).crosses(water_u) or poly.intersects(water_u):
                    continue        # never label a landmark from across the water
            if self._clear(poly, "landmark"):
                out.append({"poly": poly, "inside": inside,
                            "rec": {"kind": "landmark_faint" if lm.get("faint") else "landmark",
                                    "lines": lines, "x": px, "y": py, "size": size, "tracking": tr,
                                    "lead": lead, "angle": 0, "font": "Body"}})
        return out

    def _road_options(self, lm, near, reach):
        """A road used as a landmark is labelled like every other landmark: level, beside the road,
        near the circle it anchors."""
        words = lm["label"].replace("|", " ").split()
        flat = " ".join(words)
        forms = [flat.replace(" ", "|", 1) if len(words) > 2 else flat]
        forms += [f.replace("|", " ").rsplit(" ", 1)[0] + "|" + f.replace("|", " ").rsplit(" ", 1)[1]
                  for f in forms if len(words) > 1]
        road = lm["shape"]
        band = road.buffer(2.2)
        size, tr = STREET_LABEL_PT, 0.6
        lead = size + 1.4
        out = []
        for text in forms:
            lines = text.split("|")
            bw = max(self._text_w(l, "Body", size, tr) for l in lines) + 3
            bh = lead * len(lines) + 1.5
            cands = []
            for ln in _lines_of(road):
                t = 0.0
                while t <= ln.length:
                    pt = ln.interpolate(t)
                    d = min(pt.distance(a) for a in near)
                    if d <= reach:
                        p0 = ln.interpolate(max(0.0, t - 3))
                        p1 = ln.interpolate(min(ln.length, t + 3))
                        dx, dy = p1.x - p0.x, p1.y - p0.y
                        norm = math.hypot(dx, dy) or 1.0
                        for side in (1, -1):        # perpendicular to the road, either side
                            nx_, ny_ = -dy / norm * side, dx / norm * side
                            ext = abs(nx_) * bw / 2 + abs(ny_) * bh / 2
                            cands.append((d, pt.x + nx_ * (ext + 3.5), pt.y + ny_ * (ext + 3.5)))
                    t += 3
            for _, x, y in sorted(cands):
                poly = self._box_poly(x, y, bw, bh)
                if poly.intersects(band) or poly.distance(road) > 6:
                    continue
                if self._clear(poly, "road_anchor"):
                    out.append({"poly": poly, "inside": False,
                                "rec": {"kind": "landmark", "lines": lines, "x": x, "y": y, "size": size,
                                        "tracking": tr, "lead": lead, "angle": 0, "font": "Body"}})
        return out

    def _place_required(self, secret_hit):
        """Stop names and landmark labels are placed as one problem. Each item lists its
        positions best first; a depth-first search takes the best combination with no overlaps,
        swapping in the next landmark for a circle when one will not fit. Every item that
        cannot be placed is reported in the same run."""
        mm, rep = self.mm, self.mm.report
        reach = LANDMARK_REACH_M * self.s
        inner = self.plate.buffer(-6)
        full = [k for k in range(len(mm.areas)) if mm.group[k] == k and k not in mm.ghosts]
        items = []
        # café symbols: reserved before any label is placed
        self.cafe_marks, self.cafes_placed = [], []
        for c in mm.cafes:
            x, y = self.T(*c["xy"])
            # a grown circle may now cover a café chosen against the original circles
            if inner.contains(Point(x, y)) and not any(
                    a.buffer(CAFE_R + 2).contains(Point(x, y)) for a in self.area_shapes):
                self.cafe_marks.append((x, y, c))
        self.furniture = self.furniture + [Point(x, y).buffer(CAFE_R + 1.2) for x, y, _ in self.cafe_marks]
        # start marker: reserved first, its label required
        self.start_mark = None
        if getattr(mm, "start", None):
            x, y = self.T(*mm.start["xy"])
            if not inner.contains(Point(x, y)):
                rep["errors"].append("start: the start corner falls off the plate")
            elif any(a.buffer(START_R).intersects(Point(x, y)) for a in self.area_shapes):
                rep["errors"].append("start: the start corner sits inside a circle as printed")
            else:
                self.start_mark = (x, y)
                self.furniture = self.furniture + [Point(x, y).buffer(START_R + 1.2)]
                items.append({"what": "start label", "required": True, "start": True,
                              "options": self._point_options(x, y, "Start", "start")})
        for x, y, c in self.cafe_marks[:CAFE_PICKS * 2]:
            items.append({"what": f"café '{c['name']}'", "required": False, "cafe": c,
                          "options": self._point_options(x, y, c["name"], "cafe")})
        pinned_outlines = [lm for lm in self.landmarks if lm["kind"] == "outline"]
        # pinned road landmarks: fewest positions, so first
        for lm in [l for l in self.landmarks if l["kind"] == "road"]:
            near = [self.area_shapes[k] for k in full if lm["shape"].distance(self.area_shapes[k]) <= reach]
            if near:
                items.append({"what": f"road landmark '{lm['name']}'", "required": True,
                              "options": self._road_options(lm, near, reach)})
        # stop names: kept off pinned landmark outlines
        base_furniture = list(self.furniture)
        self.furniture = base_furniture + [lm["shape"] for lm in pinned_outlines if not lm.get("faint")]
        for i in range(1, len(mm.areas) + 1):
            if (i - 1) in mm.ghosts:      # named on its own page
                continue
            zo = self._zone_options(i)
            fl = [o for o in zo if o["rec"].get("floated")][:ZONE_OPTIONS]
            bs = [o for o in zo if not o["rec"].get("floated")][:ZONE_OPTIONS // 2]
            items.append({"what": f"stop name {mm.numbers[i - 1]}", "required": True, "zone": i,
                          "options": fl + bs})
        self.furniture = base_furniture
        # pinned outline landmarks: required only near a full circle on this page
        for k, lm in enumerate(pinned_outlines):
            others = [o["shape"] for o in pinned_outlines if o is not lm and not o.get("faint")]
            need = any(lm["shape"].distance(self.area_shapes[j]) <= reach for j in full)
            items.append({"what": f"landmark '{lm['label'].replace('|', ' ')}'", "required": need,
                          "options": self._outline_options(lm, others)})
        # automatic landmarks: one slot per circle, filled by its best candidate that fits
        slot_alts = {}
        if mm.auto_landmarks:
            furn = unary_union(self.furniture)
            pinned_shapes = [o["shape"] for o in pinned_outlines if not o.get("faint")]
            water_m = unary_union(mm.water) if mm.water else None

            def across_water(c, j):
                if water_m is None or c["poly"].intersects(water_m):
                    return False
                from shapely.ops import nearest_points
                cx, cy, _ = mm.areas[j]
                a_pt, b_pt = nearest_points(Point(cx, cy), c["poly"])
                return LineString([a_pt, b_pt]).intersects(water_m)

            def score(c, j):
                return mm.landmark_score(c, j) - (1.0 if across_water(c, j) else 0.0)

            for j in full:
                ranked = sorted((c for c in mm.landmark_pool if c["dists"].get(j, 1e9) <= LANDMARK_REACH_M),
                                key=lambda c: -score(c, j))
                opts, names = [], []
                for cand in ranked:
                    g = cand["poly"]
                    if not g.intersects(self.clip_m):
                        continue
                    shp = self.Tg(g.intersection(self.clip_m))
                    if shp.intersection(inner).is_empty or \
                            shp.intersection(inner).distance(self.area_shapes[j]) > reach:
                        continue                       # must be on the map, within reach
                    lm = dict(cand, shape=shp)
                    if cand["kind"] == "outline":
                        if not lm["faint"] and shp.intersects(furn):
                            continue
                        pos = self._outline_options(lm, pinned_shapes)
                    else:
                        pos = self._road_options(lm, [self.area_shapes[j]], reach)
                    pos = pos[:LANDMARK_POSITIONS]
                    if not pos:
                        continue
                    for o in pos:
                        o["lm"] = lm
                        o["cost"] = 0.6 * len(names) + 0.02 * pos.index(o)
                    opts += pos
                    names.append(cand["name"])
                    if len(names) >= LANDMARK_CANDIDATES_PER_CIRCLE:
                        break
                slot_alts[j] = names
                items.append({"what": f"landmark for circle {mm.numbers[j]}", "required": True, "slot": j,
                              "options": opts})

        def blocker(lm):
            return None if lm.get("faint") or lm["kind"] == "road" else lm["shape"]

        # each circle's landmark sits right after its stop name: they compete for the same room
        def key(it):
            if "zone" in it:
                return (1, mm.group[it["zone"] - 1], 0)
            if "slot" in it:
                return (1, it["slot"], 1)
            return (0 if it["what"].startswith("road") else 2, 0, 0)
        items.sort(key=key)

        placed, shapes, chosen = [], [], []       # placed: (poly, buffered); shapes: chosen outlines
        assign = [None] * len(items)

        def covered(j):
            for lm in chosen:
                part = lm["shape"].intersection(inner)
                if not part.is_empty and part.distance(self.area_shapes[j]) <= reach:
                    return True
            return False

        def fits(opt):
            if opt.get("lm") is not None and any(c["name"] == opt["lm"]["name"] for c in chosen):
                return False                          # reuse goes through the sharing fallback
            P = opt["poly"]
            if any(P.intersects(qb) for _, qb in placed):
                return False
            own = opt.get("lm")
            for shp, lm in shapes:
                if lm is own:
                    continue
                if P.intersects(shp):
                    return False
            if own is not None:
                b = blocker(own)
                if b is not None and any(b.intersects(q) for q, _ in placed):
                    return False
            return True

        # ---- constraint search over precomputed conflicts (bitmasks)
        SHARE = 1.5
        flat = []                                  # (item index, option)
        for i, it in enumerate(items):
            for o in sorted(it["options"], key=lambda o: o.get("cost", 0.0)):
                o["_id"] = len(flat)
                flat.append((i, o))
        n_opt = len(flat)
        item_mask = [0] * len(items)
        for oid, (i, o) in enumerate(flat):
            item_mask[i] |= 1 << oid
        bufs = [o["poly"].buffer(1.4) for _, o in flat]
        blks = [blocker(o["lm"]) if o.get("lm") is not None else None for _, o in flat]
        conflict = [0] * n_opt
        from shapely.strtree import STRtree
        geoms = [b for b in bufs] + [b for b in blks if b is not None]
        owner = list(range(n_opt)) + [k for k, b in enumerate(blks) if b is not None]
        tree = STRtree(geoms)
        for a_id, (ia, oa) in enumerate(flat):
            for q in [oa["poly"]] + ([blks[a_id]] if blks[a_id] is not None else []):
                for gi in tree.query(q):
                    b_id = owner[gi]
                    ib = flat[b_id][0]
                    if ib == ia:
                        continue
                    g = geoms[gi]
                    if q is oa["poly"] and gi < n_opt:
                        hit = oa["poly"].intersects(bufs[b_id])
                    else:
                        hit = q.intersects(g)
                    if hit:
                        conflict[a_id] |= 1 << b_id
                        conflict[b_id] |= 1 << a_id
        # one landmark serves one circle unless shared through the fallback
        byname = {}
        for oid, (i, o) in enumerate(flat):
            if o.get("lm") is not None:
                byname.setdefault(o["lm"]["name"], []).append(oid)
        for ids in byname.values():
            for x in ids:
                for y in ids:
                    if flat[x][0] != flat[y][0]:
                        conflict[x] |= 1 << y
        covers = [0] * n_opt                        # slots a chosen landmark option can cover
        slot_items = {it["slot"]: i for i, it in enumerate(items) if "slot" in it}
        for oid, (i, o) in enumerate(flat):
            lm = o.get("lm")
            if lm is None:
                continue
            part = lm["shape"].intersection(inner)
            for j, si in slot_items.items():
                if si != i and not part.is_empty and part.distance(self.area_shapes[j]) <= reach:
                    covers[oid] |= 1 << si
        order_ids = [[oid for oid, (i, _) in enumerate(flat) if i == k] for k in range(len(items))]
        budget = [SEARCH_BUDGET]

        class Out(Exception):
            pass

        costs = [o.get("cost", 0.0) for _, o in flat]

        def feasible(doms, optional):
            """Cheapest complete placement for one landmark set: most constrained label first,
            branch and bound on position cost, a fixed number of steps per set."""
            best = {"cost": float("inf"), "picks": None}
            local = [SET_BUDGET]
            picks = {}

            def lb(allowed):
                t = 0.0
                for i in doms:
                    if i in picks:
                        continue
                    m = doms[i] & allowed
                    if not m:
                        if i in optional:
                            t += 2.0
                            continue
                        return None
                    t += costs[(m & -m).bit_length() - 1]   # options are sorted cheapest first
                return t

            def go(allowed, cost):
                budget[0] -= 1
                local[0] -= 1
                if budget[0] < 0:
                    raise Out()
                if local[0] < 0:
                    return
                bnd = lb(allowed)
                if bnd is None or cost + bnd >= best["cost"] - 1e-9:
                    return
                left = [i for i in doms if i not in picks]
                if not left:
                    best["cost"], best["picks"] = cost, dict(picks)
                    return
                n, i = min(((doms[i] & allowed).bit_count(), i) for i in left)
                for oid in order_ids[i]:
                    if doms[i] >> oid & 1 and allowed >> oid & 1:
                        picks[i] = oid
                        go(allowed & ~conflict[oid], cost + costs[oid])
                        del picks[i]
                if i in optional or n == 0 and i in optional:
                    picks[i] = None
                    go(allowed, cost + 2.0)
                    del picks[i]
            go((1 << n_opt) - 1, 0.0)
            return best["picks"]

        # landmark sets in order of quality: rank 0 is each circle's best candidate
        slot_idx = [i for i, it in enumerate(items) if "slot" in it]
        cands = {}
        for i in slot_idx:
            names = []
            for oid in order_ids[i]:
                nm = flat[oid][1]["lm"]["name"]
                if nm not in names:
                    names.append(nm)
            names.sort(key=lambda nm: slot_alts[items[i]["slot"]].index(nm))
            cands[i] = names
        def rank_cost(i, r):
            return SHARE if r == len(cands[i]) else 0.6 * r
        import heapq as _hq
        start = tuple(0 for _ in slot_idx)
        heap = [(sum(rank_cost(i, 0) for i in slot_idx), start)]
        seen = {start}
        assign, ok, tried = [None] * len(items), False, 0
        optional = {i for i, it in enumerate(items) if not it["required"]}
        try:
            while heap and tried < 3000:
                c, ranks = _hq.heappop(heap)
                for k, i in enumerate(slot_idx):          # neighbours: one slot one rank worse
                    if ranks[k] < len(cands[i]):
                        nr = ranks[:k] + (ranks[k] + 1,) + ranks[k + 1:]
                        if nr not in seen:
                            seen.add(nr)
                            _hq.heappush(heap, (c - rank_cost(i, ranks[k]) + rank_cost(i, ranks[k] + 1), nr))
                pick = {i: (cands[i][r] if r < len(cands[i]) else None) for i, r in zip(slot_idx, ranks)}
                names = [nm for nm in pick.values() if nm]
                if len(names) != len(set(names)):
                    continue
                tried += 1
                doms = {}
                for i in range(len(items)):
                    if i in pick:
                        if pick[i] is None:
                            continue
                        doms[i] = sum(1 << oid for oid in order_ids[i]
                                      if flat[oid][1]["lm"]["name"] == pick[i])
                    else:
                        doms[i] = item_mask[i]
                res = feasible(doms, optional)
                if res is None:
                    continue
                cov = 0
                for oid in res.values():
                    if oid is not None:
                        cov |= covers[oid]
                if any(pick[i] is None and not (cov >> i & 1) for i in slot_idx):
                    continue
                for i in range(len(items)):
                    if i in res and res[i] is not None:
                        assign[i] = flat[res[i]][1]
                    elif i in pick and pick[i] is None:
                        assign[i] = "covered"
                ok = True
                rep["landmark_sets_tried"] = tried
                break
        except Out:
            rep["warnings"].append("label: search budget reached before a complete placement was found")
        rep["search_nodes"] = SEARCH_BUDGET - budget[0]
        if not ok:
            # one-run diagnosis: place greedily, report every required item that cannot fit
            placed.clear(); shapes.clear(); chosen.clear()
            assign = [None] * len(items)
            for i, it in enumerate(items):
                for opt in it["options"]:
                    if fits(opt):
                        placed.append((opt["poly"], opt["poly"].buffer(1.4)))
                        if opt.get("lm") is not None:
                            chosen.append(opt["lm"])
                            if blocker(opt["lm"]) is not None:
                                shapes.append((blocker(opt["lm"]), opt["lm"]))
                        assign[i] = opt
                        break
                if assign[i] is None and "slot" in it and covered(it["slot"]):
                    assign[i] = "covered"
                if assign[i] is None and it["required"]:
                    if "slot" in it:
                        tried = ", ".join(slot_alts.get(it["slot"], [])) or "none on the map"
                        rep["errors"].append(f"label: no landmark for circle {mm.numbers[it['slot']]} fits "
                                             f"(tried: {tried})")
                    elif not it["options"]:
                        rep["errors"].append(f"label: {it['what']} has no collision-free position")
                    else:
                        rep["errors"].append(f"label: {it['what']} has no position clear of the other "
                                             f"required labels")
        # commit: at most CAFE_PICKS cafés, best first
        n_cafe = 0
        for k2, (it, a) in enumerate(zip(items, assign)):
            if "cafe" in it and a not in (None, "covered"):
                n_cafe += 1
                if n_cafe > CAFE_PICKS:
                    assign[k2] = None
        chosen_report = []
        self.cafes_placed = []
        for it, a in zip(items, assign):
            if "cafe" in it:
                if a not in (None, "covered"):
                    self._commit(a["poly"], a["rec"])
                    self.cafes_placed.append(it["cafe"])
                continue
            if a is None:
                if not it["required"] and it["what"].startswith("landmark"):
                    rep.setdefault("labels_dropped_optional", []).append(it["what"])
                continue
            if a == "covered":
                continue
            self._commit(a["poly"], a["rec"])
            if "zone" in it and not a["rec"].get("floated"):
                rep["warnings"].append(f"label: area name {mm.numbers[it['zone'] - 1]} could not float onto its circle; "
                                       f"placed beside it")
            lm = a.get("lm")
            if lm is not None:
                self.landmarks.append(lm)
                if lm["kind"] == "road":
                    self.anchor_roads.append(lm["shape"])
                if lm.get("faint"):
                    rep.setdefault("faint_landmarks", []).append(lm["name"])
                j = it["slot"]
                chosen_report.append({"circle": mm.numbers[j], "landmark": lm["name"], "osm": lm["osm"],
                                      "ft_from_edge": round(lm["dists"][j] / FT),
                                      "score": round(mm.landmark_score(lm, j), 2),
                                      "ranked_alternatives": slot_alts.get(j, [])})
        if self.cafe_marks:
            rep["cafes_shown"] = [c["name"] for c in self.cafes_placed]
            if not self.cafes_placed:
                rep["errors"].append("café break: no room for any café label near the route")
        if mm.auto_landmarks:
            rep["landmarks_chosen"] = chosen_report
            rep["errors"] += spoiler_scan([(f"landmark {c['osm']}", c["landmark"]) for c in chosen_report],
                                          mm.m["stops"])
        outlines = [lm for lm in self.landmarks if lm["kind"] == "outline"]
        self.furniture = self.furniture + [lm["shape"] for lm in outlines if not lm.get("faint")]

    def _commit(self, poly, rec):
        self.placed.append(rec)
        self.placed_polys.append(poly)

    def _line_label(self, text, parts, font, size, tr, kind, raw_name, near_areas=None, reach=None,
                    quiet=False):
        rep = self.mm.report
        tw = self._text_w(text, font, size, tr)
        bw, bh = tw + 3, size + 2.6
        merged = linemerge(unary_union(parts)) if len(parts) > 1 else parts[0]
        lines = list(merged.geoms) if hasattr(merged, "geoms") else [merged]
        lines = [l for l in lines if isinstance(l, LineString) and l.length > bw + 6]
        cands = []
        for ln in lines:
            L = ln.length
            t = bw / 2 + 3
            while t <= L - bw / 2 - 3:
                a, b = ln.interpolate(t - bw / 2), ln.interpolate(t + bw / 2)
                chord = LineString([a, b])
                seg = _substring(ln, t - bw / 2, t + bw / 2)
                if seg is not None and seg.hausdorff_distance(chord) < 1.6:
                    ang = math.degrees(math.atan2(b.y - a.y, b.x - a.x))
                    if ang > 90:
                        ang -= 180
                    elif ang <= -90:
                        ang += 180
                    c = ln.interpolate(t)
                    score = abs(t - L / 2) / L + abs(ang) / 400
                    if near_areas:
                        dmin = min(c.distance(a) for a in near_areas)
                        if dmin > reach:
                            t += 5
                            continue
                        score = dmin + abs(ang) / 40
                    cands.append((score, c.x, c.y, ang))
                t += 5
        for _, x, y, ang in sorted(cands):
            poly = self._box_poly(x, y, bw, bh, ang)
            if self._clear(poly, kind):
                self._commit(poly, {"kind": kind, "lines": [text], "x": x, "y": y, "size": size,
                                    "tracking": tr, "lead": 0, "angle": ang, "font": font})
                return True
        if quiet:
            return False
        rep["labels"]["dropped"].append({"text": raw_name, "reason": "no straight, clear stretch "
                                         "long enough at the type floor" if not cands else
                                         "every candidate position collided"})
        return False


def _substring(ln, a, b):
    from shapely.ops import substring
    try:
        return substring(ln, a, b)
    except Exception:
        return None


# ------------------------------------------------------------------ drawing

def draw(book, lay):
    """Render a Layout onto the book's current page."""
    from reportlab.lib.colors import HexColor
    c, p, tint = book.c, book.p, _tint
    x0, y0, w, h = lay.box
    water = p.get("water", HexColor("#C9D9DE"))
    c.saveState()
    path = c.beginPath()
    path.rect(x0, y0, w, h)
    c.clipPath(path, stroke=0, fill=0)
    # plate
    c.setFillColor(tint(p["paper"], 0.55))
    c.rect(x0, y0, w, h, stroke=0, fill=1)
    _fill(c, lay.water, water)
    c.setLineCap(1)
    c.setLineJoin(1)
    # faint bands for main streets and the streets the route uses; landmarks as quiet blocks
    c.setStrokeColor(tint(p["gold"], 0.80))
    for cls, g, _, bridge in lay.streets:
        c.setLineWidth(3.4 if cls == "major" else 2.4)
        _stroke(c, g)
    c.setStrokeColor(tint(p["gold"], 0.62))
    c.setLineWidth(3.2)
    for g in lay.anchor_roads:       # roads that act as landmarks read a step stronger
        _stroke(c, g)
    for lm in lay.landmarks:
        if lm["kind"] != "outline":
            continue
        if lm.get("faint"):
            c.setStrokeColor(tint(p["gold"], 0.45))
            c.setLineWidth(0.6)
            c.setDash(2.4, 1.6)
            _stroke(c, lm["shape"].boundary)
            c.setDash()
        else:
            c.setStrokeColor(tint(p["gold"], 0.45))
            c.setLineWidth(0.5)
            _fill(c, [lm["shape"]], tint(p["gold"], 0.72), stroke=True)
    # hunt areas
    for k, shape in enumerate(lay.area_shapes):
        if lay.mm.group[k] != k:          # shared circle drawn once
            continue
        c.setStrokeColor(tint(p["accent"], 0.35))
        c.setLineWidth(0.8)
        c.setDash(2.2, 1.8)
        _fill(c, [shape], tint(p["gold"], AREA_TINT), alpha=0.6, stroke=True)
    c.setDash()
    # full street detail inside the circles, drawn over the shading
    for edge in (True, False):
        for cls, g in lay.circle_detail:
            if cls == "path":
                if edge:
                    continue
                c.setStrokeColor(tint(p["accent2"], 0.40)); c.setLineWidth(0.6); c.setDash(1.2, 1.2)
            else:
                c.setDash()
                wd = {"major": 2.6, "minor": 1.8, "service": 1.0}[cls]
                c.setStrokeColor(tint(p["gold"], 0.45) if edge else HexColor("#FFFFFF"))
                c.setLineWidth(wd + 0.8 if edge else wd)
            _stroke(c, g)
    c.setDash()
    # route, outside the areas only
    c.setStrokeColor(p["accent"])
    c.setLineWidth(1.6)
    c.setDash(4, 2.6)
    _stroke(c, lay.route)
    c.setDash()
    # markers
    for c_ in getattr(lay, "cafes_placed", []):
        for x, y, cc in lay.cafe_marks:
            if cc is c_:
                _cafe_symbol(c, x, y, p["accent2"], tint(p["paper"], 0.2))
    if getattr(lay, "start_mark", None):
        _start_symbol(c, *lay.start_mark, p["accent"], tint(p["paper"], 0.2))
    for i, (mx, my) in enumerate(lay.area_centres, 1):
        c.setFillColor(p["accent"])
        c.setStrokeColor(tint(p["paper"], 0.2))
        c.setLineWidth(0.9)
        c.circle(mx, my, lay.marker_r, stroke=1, fill=1)
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont("Body", 7.6)
        c.drawCentredString(mx, my - 2.7, str(lay.mm.numbers[i - 1]))
    # labels
    for lab in lay.placed:
        col = {"zone": p["accent"], "water": p["accent2"], "park": p["accent2"],
               "street": p["ink"], "landmark": tint(p["ink"], 0.45),
               "landmark_faint": tint(p["ink"], 0.58), "road_anchor": tint(p["ink"], 0.35),
               "cafe": p["accent2"], "start": p["accent"]}[lab["kind"]]
        _label(book, lab, col, tint(p["paper"], 0.55))
    # furniture
    _north(c, lay.north, p["accent2"])
    _scale(book, lay, p["accent2"], tint(p["paper"], 0.55))
    c.setFont("Body", FURNITURE_PT)
    c.setFillColor(p["accent2"])
    c.drawRightString(x0 + w - 5, y0 + 4.5, lay.attrib_text)
    c.restoreState()
    c.setStrokeColor(tint(p["accent2"], 0.4))
    c.setLineWidth(0.7)
    c.rect(x0, y0, w, h, stroke=1, fill=0)


def _start_symbol(c, x, y, col, ring):
    """A hollow disc with an S: where the walk begins. Not a stop, so not a filled disc."""
    c.setFillColor(ring)
    c.setStrokeColor(col)
    c.setLineWidth(1.1)
    c.circle(x, y, START_R, stroke=1, fill=1)
    c.setFillColor(col)
    c.setFont("Body", 6.4)
    c.drawCentredString(x, y - 2.2, "S")


def _cafe_symbol(c, x, y, col, ring):
    """A small cup in a disc: the café break."""
    c.setFillColor(col)
    c.setStrokeColor(ring)
    c.setLineWidth(0.6)
    c.circle(x, y, CAFE_R, stroke=1, fill=1)
    c.setFillColor(ring)
    c.setStrokeColor(ring)
    c.setLineWidth(0.5)
    c.rect(x - 1.6, y - 1.3, 2.6, 2.4, stroke=0, fill=1)       # cup
    c.circle(x + 1.5, y + 0.1, 0.75, stroke=1, fill=0)           # handle
    c.line(x - 2.2, y - 1.7, x + 1.6, y - 1.7)                   # saucer


def _tint(col, f):
    from reportlab.lib.colors import Color
    return Color(col.red + (1 - col.red) * f, col.green + (1 - col.green) * f,
                 col.blue + (1 - col.blue) * f)


def _polys_of(g):
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, MultiPolygon):
        return list(g.geoms)
    if hasattr(g, "geoms"):
        return [x for gg in g.geoms for x in _polys_of(gg)]
    return []


def _lines_of(g):
    if isinstance(g, LineString):
        return [g]
    if isinstance(g, MultiLineString) or hasattr(g, "geoms"):
        return [x for gg in g.geoms for x in _lines_of(gg)]
    return []


def _fill(c, geoms, col, alpha=None, stroke=False):
    c.setFillColor(col)
    if alpha is not None:
        c.setFillAlpha(alpha)
    for g in geoms:
        for pg in _polys_of(g):
            path = c.beginPath()
            for ring in [pg.exterior] + list(pg.interiors):
                cs = list(ring.coords)
                path.moveTo(*cs[0])
                for q in cs[1:]:
                    path.lineTo(*q)
                path.close()
            c.drawPath(path, stroke=1 if stroke else 0, fill=1, fillMode=0)
    if alpha is not None:
        c.setFillAlpha(1)


def _stroke(c, g):
    for ln in _lines_of(g):
        cs = list(ln.coords)
        if len(cs) < 2:
            continue
        path = c.beginPath()
        path.moveTo(*cs[0])
        for q in cs[1:]:
            path.lineTo(*q)
        c.drawPath(path, stroke=1, fill=0)


def _label(book, lab, col, halo):
    c = book.c
    font, size, tr = lab["font"], lab["size"], lab["tracking"]
    lines = lab["lines"]
    lead = lab["lead"] or size
    c.saveState()
    c.translate(lab["x"], lab["y"])
    if lab["angle"]:
        c.rotate(lab["angle"])
    top = (len(lines) - 1) * lead / 2
    for mode in (1, 0):
        for j, ln in enumerate(lines):
            ww = book.text_width(ln, font, size) + tr * (len(ln) - 1)
            xx = -ww / 2
            yy = top - j * lead - size * 0.34
            t = c.beginText()
            t.setFont(font, size)
            t._code.append(f"{mode} Tr")   # text render mode persists across BT/ET; set it explicitly
            t.setCharSpace(tr)
            t.setTextOrigin(xx, yy)
            t.textOut(ln)
            if mode == 1:
                c.setStrokeColor(halo)
                c.setLineWidth(1.8)
                c.setLineJoin(1)
            else:
                c.setFillColor(col)
            c.drawText(t)
    c.restoreState()


def _north(c, at, col):
    nx, ny = at
    c.setStrokeColor(col)
    c.setFillColor(col)
    c.setLineWidth(1.0)
    c.line(nx, ny - 10, nx, ny + 8)
    path = c.beginPath()
    path.moveTo(nx, ny + 13)
    path.lineTo(nx - 3.4, ny + 6)
    path.lineTo(nx + 3.4, ny + 6)
    path.close()
    c.drawPath(path, stroke=0, fill=1)
    c.setFont("Body", FURNITURE_PT + 0.5)
    c.drawCentredString(nx, ny - 18, "N")


def _scale(book, lay, col, halo):
    c = book.c
    sx, sy = lay.scale_at
    L = lay.scale_len
    c.setFillColor(halo)
    c.rect(sx - 3, sy - 4, L + 30, 15, stroke=0, fill=1)
    c.setStrokeColor(col)
    c.setLineWidth(0.9)
    c.line(sx, sy, sx + L, sy)
    for xx in (sx, sx + L / 2, sx + L):
        c.line(xx, sy, xx, sy + 3)
    c.setFillColor(col)
    c.rect(sx, sy, L / 2, 1.6, stroke=0, fill=1)
    c.setFont("Body", FURNITURE_PT)
    c.drawString(sx, sy + 4.5, "0")
    c.drawString(sx + L + 3, sy - 0.5, lay.scale_text)
    note = getattr(lay, "scale_note", None)
    if note:
        c.setFillColor(halo)
        c.rect(sx - 3, sy - 12, c.stringWidth(note, "Body-Italic", FURNITURE_PT) + 6, 8, stroke=0, fill=1)
        c.setFillColor(col)
        c.setFont("Body-Italic", FURNITURE_PT)
        c.drawString(sx, sy - 9.5, note)


# ------------------------------------------------------------------ pre-divider scan

def pre_divider_texts(spec):
    """Every string that appears before the spoiler divider, with a location tag."""
    out = []

    def walk(where, v):
        if isinstance(v, str):
            out.append((where, v))
        elif isinstance(v, (list, tuple)):
            for k, x in enumerate(v):
                walk(f"{where}[{k}]", x)
        elif isinstance(v, dict):
            for k, x in v.items():
                if k in ("target", "view_from", "secret_terms", "answer_name", "data", "labels",
                         "sources", "evidence", "action", "decoy", "review"):   # not printed
                    continue
                walk(f"{where}.{k}", x)

    for k in ("cover_kicker", "title_line1", "title_line2", "subtitle", "subtitle_lines",
              "cover_tagline_lines", "how_to_play", "acts", "maker"):
        if k in spec:
            walk(k, spec[k])
    m = spec.get("map", {})
    for k in ("title", "route_note", "mechanic_note", "representation_note"):
        if k in m:
            walk(f"map.{k}", m[k])
    for i, st in enumerate(m.get("stops", []), 1):
        walk(f"map.stops[{i}].zone", st.get("zone", ""))
    for i, st in enumerate(spec.get("stops", []), 1):
        walk(f"riddle {i}", st.get("riddle", {}))
    return out


def record(out_pdf, model, spec_path, extra_files):
    """Write the reproducibility record next to the PDF."""
    def h(p):
        return _sha256(open(p, "rb").read()) if p and os.path.exists(p) else None
    rec = {"generator": MAPGEN_VERSION,
           "spec": {"path": os.path.basename(spec_path), "sha256": h(spec_path)},
           "code": {os.path.basename(p): h(p) for p in extra_files},
           "output": {"pdf": os.path.basename(out_pdf), "sha256": h(out_pdf)},
           "status": "draft — pending author review",
           "report": model.report}
    path = os.path.splitext(out_pdf)[0] + "_record.json"
    with open(path, "w") as f:
        json.dump(rec, f, indent=2, ensure_ascii=False)
    return path
