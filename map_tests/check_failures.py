#!/usr/bin/env python3
"""Negative tests for map schema v2: each broken spec must be blocked.

Usage: python map_tests/check_failures.py
Uses the bath_map_test_01 fixture and its cached data. Prints PASS/FAIL per case.
"""
import copy, importlib.util, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "chapbook_skill", "scripts"))
import engine, mapgen

FIX = os.path.join(HERE, "bath_map_test_01")
spec_mod = importlib.util.spec_from_file_location("s", os.path.join(FIX, "map_spec.py"))
mod = importlib.util.module_from_spec(spec_mod); spec_mod.loader.exec_module(mod)
BASE = mod.SPEC
engine.SPEC_DIR = FIX


def blocked(mutate, expect):
    """True only if the build stops AND one of its errors names the expected reason."""
    s = copy.deepcopy(BASE)
    mutate(s)
    out = os.path.join(tempfile.mkdtemp(), "t.pdf")
    try:
        engine.Book(s, out).map_only()
    except mapgen.MapError as e:
        lines = [ln.strip() for ln in str(e).splitlines() if ln.strip()]
        hit = [ln for ln in lines if expect in ln]
        return (True, hit[0]) if hit else (False, f"blocked for another reason: {lines[-1]}")
    return False, "rendered"


FLOR = os.path.join(HERE, "florence_map_test_02")


def on_fixture(folder, f):
    """Run a case against another fixture's spec."""
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), folder)
    def mut(s):
        sp = importlib.util.spec_from_file_location("x", os.path.join(d, "map_spec.py"))
        fm = importlib.util.module_from_spec(sp); sp.loader.exec_module(fm)
        s.clear(); s.update(copy.deepcopy(fm.SPEC))
        engine.SPEC_DIR = d
        f(s["map"])
    return mut


def on_florence(f):
    """Run a case against the Florence fixture (long route: the planner splits it in two)."""
    def mut(s):
        sp = importlib.util.spec_from_file_location("f", os.path.join(FLOR, "map_spec.py"))
        fm = importlib.util.module_from_spec(sp); sp.loader.exec_module(fm)
        s.clear(); s.update(copy.deepcopy(fm.SPEC))
        engine.SPEC_DIR = FLOR
        f(s["map"])
    return mut


def _all_names():
    """Every candidate name in the Bath data, so the exclusion list leaves nothing."""
    engine.SPEC_DIR = FIX
    s = copy.deepcopy(BASE)
    s["map"]["landmarks"] = "auto"
    mm = mapgen.MapModel(s["map"], FIX)
    return [c["name"] for c in mm.landmark_pool]


ALL_NAMES = _all_names()


def m(f):
    return lambda s: f(s["map"])

CASES = [
    ("v1 schema retired", m(lambda mp: mp.pop("version")), 'schema v2 required'),
    ("secret term in route note", m(lambda mp: mp.__setitem__("route_note", mp["route_note"] + " Finish at the fountain.")), "route_note contains 'fountain'"),
    ("secret term in zone label", m(lambda mp: mp["stops"][2].__setitem__("zone", "BY THE|OBELISK")), 'zone label 3 contains'),
    ("cross-stop leak in title", m(lambda mp: mp.__setitem__("title", "Abbey to Avon")), "map title contains 'Abbey'"),
    ("ticketed stop not last", m(lambda mp: mp["stops"][1].__setitem__("access", "ticketed")), 'is ticketed but is not the last'),
    ("area radius below floor", m(lambda mp: mp["stops"][0].__setitem__("area_radius_ft", 60)), 'below the 100 ft'),
    ("overlapping areas", m(lambda mp: [st.__setitem__("area_radius_ft", 300) for st in mp["stops"]]), 'overlap'),
    ("claimed distance contradicts route", m(lambda mp: mp["route"].__setitem__("claimed_distance_m", 1500)), 'claimed 1500 m'),
    ("unknown OSM target", m(lambda mp: mp["stops"][0].__setitem__("target", "way/1")), 'not found in cached OSM data'),
    ("circle with no landmark within 500 ft", m(lambda mp: mp.__setitem__("landmarks", mp["landmarks"][:1])), 'no landmark within 500 ft'),
    ("road landmark not found", m(lambda mp: mp["landmarks"].append({"road": "Nowhere Street"})), 'no mapped road named'),
    ("retired map style", m(lambda mp: mp.__setitem__("style", "detailed")), 'is retired'),
    ("map placeholder not replaced", m(lambda mp: mp.__setitem__("placeholder", True)), 'map not written yet'),
    ("circle needs more than the growth cap on any plan", on_fixture("barcelona_map_test_03", lambda mp: mp.__setitem__("stops", [mp["stops"][0], mp["stops"][1], mp["stops"][7]])), 'even at the 400 ft cap'),
    ("automatic landmarks: nothing usable near a circle", m(lambda mp: (mp.__setitem__("landmarks", "auto"), mp.__setitem__("landmark_exclude", ALL_NAMES))), 'has no landmark within 500 ft'),
    ("data hash mismatch", m(lambda mp: mp["data"].__setitem__("manifest", "../bath_map_test_01/data/manifest_tampered.json")), 'does not match its manifest hash'),
]

# tampered manifest for the hash case
import json
man = json.load(open(os.path.join(FIX, "data", "manifest.json")))
man["files"][0]["sha256_uncompressed"] = "0" * 64
tp = os.path.join(FIX, "data", "manifest_tampered.json")
json.dump(man, open(tp, "w"))
fails = 0
try:
    for name, mut, expect in CASES:
        engine.SPEC_DIR = FIX
        ok, msg = blocked(mut, expect)
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {msg}")
finally:
    os.remove(tp)
print(f"{len(CASES) - fails}/{len(CASES)} blocked as expected")
sys.exit(1 if fails else 0)
