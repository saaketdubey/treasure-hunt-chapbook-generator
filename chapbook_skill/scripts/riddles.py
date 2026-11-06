# -*- coding: utf-8 -*-
"""Riddle review (backlog block D): riddle data fields, the hint rule, the pass/fail rubric and
the cold-solver report. Imported by engine.py; the build stops on an error here before drawing.

Severities follow provenance.py: automated checks block; a failed human item blocks unless the
review carries an `override` reason; human judgement (does the evidence really show, does the
action really produce the answer) stays with the author and is listed as unperformed.

Riddle data fields (see references/craft.md, Riddles):
    evidence : list of {"text": str, "where": "public" | "interior"}, two or more
    action   : str — the one thing the reader does
    decoy    : {"name": str, "where": str, "why_wrong": str}
    hint     : str
    review   : {item: "pass" | {"result": "pass"|"fail", "note": str}, ..., "override": str?}

The cold-solver report is cold_solver.json beside the spec, written by a reader who saw only the
packet printed by scripts/riddle_pages.py (packet_text below; its hash dates the report):
    {"riddles_sha256": "...", "reader": "...", "date": "YYYY-MM-DD",
     "results": {"1": {"named": "...", "basis": "hint"|"evidence"|"none", "line": "..."}, ...},
     "intro_leak": "No" | "Yes: ..."}   # anything outside the riddles that gave an answer away
"""
import hashlib
import json
import os
import re
import access

RUBRIC = {
    "hint_recognition_only": "the hint adds recognition only and does not locate (craft.md, hint rule)",
    "evidence_observable": "every evidence item can be seen at the stop's access level and hours",
    "decoy_reachable": "the decoy is inside the circle or on the route, with no ticket or opening hour",
    "action_matches_answer": "doing the action produces the thing the answer page names",
    "no_shared_evidence": "no evidence item would also fit another stop's answer",
}
KID_RUBRIC = {
    "kid_countable": "evidence is countable or pointable from a child's height",
    "kid_plain_words": "architectural and historical terms are glossed in the same line",
    "kid_hint_names_decoy": "the hint names the decoy outright",
    "kid_single_action": "the instruction stanza is one concrete action",
}
EVIDENCE_WHERE = ("public", "interior")
INTERIOR_OK_ACCESS = ("ticketed", "hours_limited")

# Phrases that locate rather than recognise. Deliberately literal; the human rubric item covers
# what a list cannot.
LOCATE_PATTERNS = [
    (r"\bcorner of\b", "names a street corner"),
    (r"\b(north|south|east|west)[- ]?(east|west)?(ern)?\s+(side|corner|end|edge)\b", "names a side of the square or block"),
    (r"\b(north|south|east|west)(-?(east|west))?(ern)?\s+of\b", "gives a compass direction from a named place"),
    (r"\b(across|opposite)\s+from\b", "positions the target relative to a named place"),
    (r"\b(next|adjacent)\s+to\b", "positions the target relative to a named place"),
    (r"\bbeside\s+the\b", "positions the target relative to a named place"),
    (r"\b(number|no\.|nos?\.)\s*\d+", "gives a house number"),
    (r"\b\d+\s+[A-Z][a-z]+\s+(Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Lane|Place|Square|Via|Piazza|Rue|Calle|Strasse|Straße)\b",
     "gives an address"),
    (r"\b(on|along|down|up)\s+[A-Z][A-Za-z']+(\s+[A-Z][A-Za-z']+)*\s+(Street|Avenue|Road|Lane|Boulevard|Via|Piazza|Rue|Calle|Strasse|Straße)\b",
     "names the street"),
    (r"\b(West|East|North|South)\s+\d+(st|nd|rd|th)\b", "names a numbered street"),
    (r"\b\d+(st|nd|rd|th)\s+(Street|Avenue|St\.?|Ave\.?)\b", "names a numbered street"),
    (r"\b(two|three|four|five|a few|\d+)\s+(blocks?|minutes?|doors?)\s+(north|south|east|west|away|from|along)\b",
     "gives a distance from a named place"),
]

STOPWORDS = set("""a an the and or of in on at to from with by for is are was were be been its it this that
these those one two three its their there here you your look find count read see stand under over
near where which what who when than then".""".split())


class RiddleError(Exception):
    pass


# ---------------------------------------------------------------- helpers

def _words(s):
    return {w for w in re.findall(r"[a-z]+", s.lower()) if len(w) > 3 and w not in STOPWORDS}


def start_caption(spec, spec_dir):
    """The start line the map page prints, taken from a full layout of the map page (circles
    that grow can move the start); None when the map is not built yet or cannot be laid out."""
    m = spec.get("map", {})
    if not spec_dir or m.get("placeholder") or m.get("version") != 2:
        return None
    try:
        import engine   # lazy: engine imports this module
        old = engine.SPEC_DIR
        engine.SPEC_DIR = spec_dir
        try:
            return engine.printed_start_caption(spec)
        finally:
            engine.SPEC_DIR = old
    except Exception:
        return None


def packet_text(spec, spec_dir=None):
    """The cold-solver packet: every printed pre-divider string that bears on the riddles."""
    out = []
    t = " ".join(x for x in (spec.get("title_line1"), spec.get("title_line2")) if x)
    out.append(f"{t} — {spec.get('subtitle', '')}".strip(" —"))
    hp = spec.get("how_to_play", {})
    out.append("")
    out.append(hp.get("intro", ""))
    out.append(hp.get("mechanic", ""))
    for n in hp.get("notes", []):
        out.append("· " + n)
    out.append("")
    out.append("Before you go (generated box on the same page):")
    for ln in access.box_lines(spec):
        out.append("· " + ln)
    start = start_caption(spec, spec_dir)
    if start:
        out.append("")
        out.append(f"Map page: {start}")
    out.append("")
    out.append("Map circles, in walking order (the map also labels named parks, squares and major "
               "buildings next to each circle, as any street map would):")
    for i, st in enumerate(spec.get("map", {}).get("stops", []), 1):
        out.append(f"  {i}. {st.get('zone', '').replace('|', ' ')}")
    for i, st in enumerate(spec.get("stops", []), 1):
        r = st["riddle"]
        out.append("")
        out.append(f"=== Stop {i}: {r.get('name', '')}")
        for stanza in r.get("stanzas", []):
            out.append("")
            out.extend("    " + ln for ln in stanza)
    out.append("")
    out.append("=== Hints page (printed after the last riddle; each riddle page sends the reader "
               "here only if stuck)")
    for i, st in enumerate(spec.get("stops", []), 1):
        out.append(f"    Stop {i}: " + (st["riddle"].get("hint") or ""))
    out.append("")
    out.append("Instructions for the reader: for each stop, write the specific place or object you "
               "believe is the answer and quote the line that made you sure. Then record the basis: "
               "evidence if the stanzas would have got you there without the hints page; hint only "
               "if the hint alone would have named it and the stanzas would not; none if you could not "
               "say. The order you read them in does not matter. Then the intro check: does anything "
               "outside the riddles — the intro, the notes, the Before you go box, the circle names, "
               "the start line — identify "
               "an answer or place it more precisely than a map circle with its ordinary street-map "
               "labels would? General knowledge of the city is not a leak: a famous thing inside a "
               "circle is still inside a circle. Answer with the single word No, or with Yes followed "
               "by the quoted text. Do not look anything up.")
    return "\n".join(out)



def riddles_hash(spec, spec_dir=None):
    return hashlib.sha256(packet_text(spec, spec_dir).encode()).hexdigest()


def locate_hits(text):
    hits = []
    for pat, why in LOCATE_PATTERNS:
        m = re.search(pat, text)
        if m:
            hits.append(f"'{m.group(0)}' {why}")
    return hits


# ---------------------------------------------------------------- validation

def validate(spec, spec_dir):
    """Returns (errors, warnings, report). Errors stop the build."""
    errors, warnings = [], []
    stops = spec.get("stops", [])
    map_stops = spec.get("map", {}).get("stops", [])
    kid = bool(spec.get("kid_friendly"))
    rubric = dict(RUBRIC, **(KID_RUBRIC if kid else {}))
    report = {"kid_friendly": kid, "rubric_items": rubric, "stops": [], "cold_solver": None}

    evidence_words = []
    for i, st in enumerate(stops, 1):
        r = st.get("riddle", {})
        where = f"riddle {i}"
        rep = {"stop": i, "name": r.get("name"), "review": {}, "automated": []}
        access = map_stops[i - 1].get("access", "open_air") if i - 1 < len(map_stops) else "open_air"

        ev = r.get("evidence")
        if not isinstance(ev, list) or len(ev) < 2:
            errors.append(f"{where}: `evidence` must list at least two observations")
            ev = []
        for k, e in enumerate(ev):
            if not isinstance(e, dict) or not e.get("text") or e.get("where") not in EVIDENCE_WHERE:
                errors.append(f"{where}: evidence[{k}] must be {{'text', 'where': public|interior}}")
                continue
            if e["where"] == "interior" and access not in INTERIOR_OK_ACCESS:
                errors.append(f"{where}: evidence[{k}] is interior but the map stop is `{access}`; "
                              f"a reader at street level cannot see it")
        evidence_words.append(set().union(*[_words(e["text"]) for e in ev if isinstance(e, dict)
                                            and e.get("text")]) if ev else set())

        if not isinstance(r.get("action"), str) or not r["action"].strip():
            errors.append(f"{where}: `action` (what the reader does to finish the stop) is missing")
        d = r.get("decoy")
        if not isinstance(d, dict) or not all(d.get(k) for k in ("name", "where", "why_wrong")):
            errors.append(f"{where}: `decoy` must give name, where and why_wrong")
        hint = r.get("hint")
        if not isinstance(hint, str) or not hint.strip():
            errors.append(f"{where}: `hint` is missing")
            hint = ""
        for h in locate_hits(hint):
            errors.append(f"{where}: hint locates — {h}; the map circle is the only locator")
        for h in locate_hits(" ".join(ln for stz in r.get("stanzas", []) for ln in stz)):
            warnings.append(f"{where}: a stanza may locate — {h}; check it against the hint rule")

        rv = r.get("review")
        if not isinstance(rv, dict):
            errors.append(f"{where}: `review` rubric is missing (items: {', '.join(rubric)})")
            rv = None
        fails = []
        for item, desc in (rubric.items() if rv is not None else ()):
            v = rv.get(item)
            if v == "pass":
                res, note = "pass", ""
            elif isinstance(v, dict) and v.get("result") in ("pass", "fail"):
                res, note = v["result"], v.get("note", "")
                if res == "fail" and not note:
                    errors.append(f"{where}: review.{item} fails without a note")
            else:
                errors.append(f"{where}: review.{item} must be 'pass' or {{'result', 'note'}} — {desc}")
                continue
            rep["review"][item] = {"result": res, "note": note}
            if res == "fail":
                fails.append(item)
        for item in (rv or {}):
            if item not in rubric and item != "override":
                warnings.append(f"{where}: review.{item} is not a rubric item and is ignored")
        if fails:
            if rv and rv.get("override"):
                warnings.append(f"{where}: review fails {', '.join(fails)} — overridden: {rv['override']}")
                rep["override"] = rv["override"]
            else:
                errors.append(f"{where}: review fails {', '.join(fails)}; revise the riddle or give "
                              f"review.override a reason")
        rep["automated"] = ["fields present", "interior evidence only at ticketed or hours-limited stops",
                            "hint scanned for locating phrases", "rubric complete"]
        report["stops"].append(rep)

    # cross-stop evidence overlap (D6, heuristic; the rubric item is the real check)
    for a in range(len(evidence_words)):
        for b in range(a + 1, len(evidence_words)):
            shared = evidence_words[a] & evidence_words[b]
            if len(shared) >= 2:
                warnings.append(f"riddles {a + 1} and {b + 1} share evidence words "
                                f"{sorted(shared)}; check review.no_shared_evidence")

    # cold solver
    cs_errors, cs_warnings, cs = load_cold_solver(spec, spec_dir)
    errors += cs_errors
    warnings += cs_warnings
    report["cold_solver"] = cs
    return errors, warnings, report


def load_cold_solver(spec, spec_dir):
    errors, warnings = [], []
    skip = (spec.get("riddles") or {}).get("skip_cold_solver")
    path = os.path.join(spec_dir, "cold_solver.json")
    if not os.path.exists(path):
        if skip:
            warnings.append(f"cold solver skipped: {skip}")
            return errors, warnings, {"skipped": skip}
        errors.append("cold_solver.json not found — print the packet with scripts/riddle_pages.py, "
                      "have a reader who has not seen the answers fill it in, or set "
                      "riddles.skip_cold_solver with a reason")
        return errors, warnings, None
    try:
        cs = json.load(open(path))
    except Exception as e:  # noqa
        errors.append(f"cold_solver.json unreadable: {e}")
        return errors, warnings, None
    if cs.get("riddles_sha256") != riddles_hash(spec, spec_dir):
        errors.append("cold_solver.json is stale — the riddle pages changed after the reader saw them; "
                      "print the packet again and repeat the read")
        return errors, warnings, cs
    leak = (cs.get("intro_leak") or "").strip()
    if leak and not re.match(r"(?i)^(no\b|none\b|nothing\b)", leak):
        errors.append(f"cold solver reports a leak outside the riddles — {leak}; fix the text, print "
                      f"the packet again and repeat the read")
    results = cs.get("results", {})
    n = len(spec.get("stops", []))
    for i in range(1, n + 1):
        r = results.get(str(i))
        if not isinstance(r, dict) or r.get("basis") not in ("hint", "evidence", "none"):
            errors.append(f"cold_solver.json: result for stop {i} must give basis hint|evidence|none")
            continue
        named = (r.get("named") or "").strip()
        if r["basis"] == "hint":
            errors.append(f"cold solver named stop {i} ('{named}') from the hint alone — "
                          f"line: {r.get('line', '')!r}; rewrite the hint")
        elif r["basis"] == "evidence":
            warnings.append(f"cold solver named stop {i} ('{named}') from the evidence by inference "
                            f"(line: {r.get('line', '')!r}); recorded as easy — confirm it is the answer")
            r["difficulty"] = "easy"
    return errors, warnings, cs


def record_section(report):
    return {
        "report": report,
        "automated_checks": [
            "riddle data fields present (evidence x2+, action, decoy, hint, review)",
            "interior evidence only where the map stop is ticketed or hours-limited",
            "hint scanned for locating phrases (corner, side, address, across from, numbered street, distance)",
            "rubric complete; a fail blocks without an override reason",
            "cold-solver report present, fresh, no stop named from its hint alone, no leak reported outside the riddles",
            "evidence word overlap between riddles flagged",
        ],
        "unperformed_checks": [
            "whether each evidence item is really visible on site at the hours the book allows (human)",
            "whether doing the action produces the thing the answer page names (human)",
            "whether the decoy is met without a detour (human, on site or on the map)",
            "the cold solver is a reader, not a walker: solvability on site is not tested",
        ],
    }
