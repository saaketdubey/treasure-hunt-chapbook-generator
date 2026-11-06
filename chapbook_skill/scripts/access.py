# -*- coding: utf-8 -*-
"""Access information for walkers (block E: E1, E4, E5, E8).

Each stop's access *kind* lives on its map stop (`map.stops[i].access`: open_air, ticketed,
hours_limited). A gated stop (ticketed or hours_limited) also carries an access *record* on
its book stop:

    "access": {
        "entry":    "required" | "optional",   # must the walker go in to solve the riddle?
        "summary":  "one line: hours or price",
        "fallback": "what to do if it is shut",
        "source":   "<source id>",             # the official page; url + accessed date come
    }                                          # from the source record (live-checked)

Open-air stops take no record; the kind is enough.

From those records the engine prints a generated "Before you go" box on the How to Play page
(stops by number only, never by name) and a sealed access-links page at the very back of the
book (inside the back cover: official links, stop names). Hand-written How to Play text may not mention tickets,
hours, prices or "free": access facts come only from the records.
"""

import datetime
import re

GATED = ("ticketed", "hours_limited")
KINDS = ("open_air",) + GATED
ENTRY = ("required", "optional")
RECORD_FIELDS = ("entry", "summary", "fallback", "source")
SUMMARY_MAX = 110          # characters; the summary is one printed line
STALE_DAYS = 30            # a checked date older than this at build time warns

KIND_LABEL = {"ticketed": "ticketed", "hours_limited": "limited opening hours"}

# Access talk in hand-written How to Play text. Precision over recall: walking durations
# ("an hour on foot") are fine; opening hours, prices and booking are not.
NOTE_PATTERNS = [
    r"\btickets?\b|\bticketed\b",
    r"\badmission\b|\bentry fee\b|\bentrance fee\b",
    r"\bbook(ing)? (ahead|in advance)\b|\breservations?\b",
    r"\bopening (hours|times)\b|\bopen(s)? (daily|every day|until|till|from|late)\b",
    r"\b(any|all) hours?\b|\bafter hours\b",
    r"\bcloses\b|\bclosed\b|\bclosing time\b",
    r"(?<!feel )\bfree\b",
    r"\bprices?\b|\bcosts?\b|[$£€]\s?\d",
]


class AccessError(Exception):
    pass


def kind_of(spec, i):
    """Access kind of stop i (1-based), from the map stop."""
    ms = spec.get("map", {}).get("stops", [])
    return ms[i - 1].get("access", "open_air") if i - 1 < len(ms) else "open_air"


def _sources(spec):
    return {s.get("id"): s for s in spec.get("sources", []) or []}


def _date(s):
    try:
        return datetime.date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def nice_date(s):
    d = _date(s)
    return f"{d.day} {d.strftime('%B %Y')}" if d else str(s)


def how_to_play_texts(spec):
    """Every hand-written string on the How to Play page, with its location."""
    hp = spec.get("how_to_play", {})
    out = []
    for k in ("intro", "mechanic", "checklist_title"):
        if hp.get(k):
            out.append((f"how_to_play.{k}", hp[k]))
    for k in ("steps", "checklist", "notes"):
        for j, t in enumerate(hp.get(k, []) or []):
            out.append((f"how_to_play.{k}[{j}]", t))
    return out


def scan_notes(spec):
    errors = []
    for where, t in how_to_play_texts(spec):
        for pat in NOTE_PATTERNS:
            m = re.search(pat, t, re.I)
            if m:
                errors.append(f"{where}: '{m.group(0)}' — tickets, hours, prices and 'free' come "
                              f"only from stop access records (the generated Before you go box); "
                              f"remove it from the hand-written text")
                break
    return errors


def validate(spec, today=None):
    """Returns (errors, warnings, report). Errors stop the build."""
    today = today or datetime.date.today()
    errors, warnings = [], []
    stops = spec.get("stops", [])
    srcs = _sources(spec)
    report = {"stops": []}
    seen_required = None
    for i, st in enumerate(stops, 1):
        kind = kind_of(spec, i)
        rec = st.get("access")
        where = f"stop {i}"
        rep = {"stop": i, "kind": kind}
        if kind not in KINDS:
            errors.append(f"{where}: map access kind `{kind}` is not one of {', '.join(KINDS)}")
            report["stops"].append(rep)
            continue
        if kind == "open_air":
            if rec is not None:
                errors.append(f"{where}: open-air stops take no access record; the kind is enough "
                              f"(remove `access` from the book stop, or change the map kind)")
            if seen_required:
                errors.append(f"{where}: an open-air stop follows stop {seen_required}, where "
                              f"going in is required; required-entry stops come last")
            report["stops"].append(rep)
            continue
        # gated
        if not isinstance(rec, dict):
            errors.append(f"{where}: {KIND_LABEL[kind]} stop needs an access record "
                          f"({', '.join(RECORD_FIELDS)})")
            report["stops"].append(rep)
            continue
        for f in RECORD_FIELDS:
            if not str(rec.get(f) or "").strip():
                errors.append(f"{where}: access record is missing `{f}`")
        extra = set(rec) - set(RECORD_FIELDS)
        if extra:
            errors.append(f"{where}: access record has unknown fields {sorted(extra)} — the URL "
                          f"and checked date come from the source record")
        entry = rec.get("entry")
        if entry and entry not in ENTRY:
            errors.append(f"{where}: access `entry` must be required or optional, not `{entry}`")
        summ = str(rec.get("summary") or "")
        if len(summ) > SUMMARY_MAX:
            errors.append(f"{where}: access summary is {len(summ)} characters; the limit is "
                          f"{SUMMARY_MAX} (one printed line)")
        if "\n" in summ:
            errors.append(f"{where}: access summary must be one line")
        sid = rec.get("source")
        src = srcs.get(sid) if sid else None
        if sid and src is None:
            errors.append(f"{where}: access source `{sid}` is not in `sources`")
        if src is not None:
            d = _date(src.get("accessed"))
            if d is None:
                errors.append(f"{where}: access source `{sid}` has no valid `accessed` date")
            elif (today - d).days > STALE_DAYS:
                warnings.append(f"{where}: access checked {src.get('accessed')}, "
                                f"{(today - d).days} days ago (over {STALE_DAYS}); re-read "
                                f"{src.get('url')} and update the summary and date")
            rep.update(url=src.get("url"), checked=src.get("accessed"))
        # E8: optional entry means the riddle is solved from outside
        if entry == "optional":
            inside = [k for k, e in enumerate(st.get("riddle", {}).get("evidence", []) or [], 1)
                      if isinstance(e, dict) and e.get("where") != "public"]
            if inside:
                errors.append(f"{where}: going in is optional, so every evidence item must be "
                              f"public; evidence {inside} is interior")
            if seen_required:
                errors.append(f"{where}: an optional-entry stop follows stop {seen_required}, "
                              f"where going in is required; required-entry stops come last")
        if entry == "required":
            ev = st.get("riddle", {}).get("evidence", []) or []
            if ev and all(isinstance(e, dict) and e.get("where") == "public" for e in ev):
                warnings.append(f"{where}: going in is marked required but every evidence item is "
                                f"public; consider `optional`")
            seen_required = seen_required or i
        rep.update(entry=entry, summary=summ, fallback=rec.get("fallback"))
        report["stops"].append(rep)
    errors += scan_notes(spec)
    return errors, warnings, report


# ---------------------------------------------------------------- printed text

def gated(spec):
    return [(i, st, kind_of(spec, i)) for i, st in enumerate(spec.get("stops", []), 1)
            if kind_of(spec, i) in GATED]


def box_lines(spec):
    """The generated Before you go box. Stops by number only; nothing here names a stop."""
    n = len(spec.get("stops", []))
    g = gated(spec)
    srcs = _sources(spec)
    if not g:
        return [f"All {n} stops are open-air: nothing to book or time, and every riddle is "
                f"solved from outside."]
    lines = []
    open_n = n - len(g)
    if open_n:
        lines.append(f"{open_n} of {n} stops are open-air: nothing to book or time.")
    for i, st, kind in g:
        rec = st.get("access", {})
        src = srcs.get(rec.get("source"), {})
        entry = ("you need to go in" if rec.get("entry") == "required"
                 else "going in is optional; the riddle is solved from outside")
        lines.append(f"Stop {i}, {KIND_LABEL[kind]}: {entry}. {rec.get('summary', '').rstrip('.')}. "
                     f"Checked {nice_date(src.get('accessed'))}. If it is shut: "
                     f"{rec.get('fallback', '').rstrip('.')}.")
    lines.append("Official links for checking on the day are inside the back cover. That page "
                 "names the stops; open it only if you need to.")
    return lines


def link_entries(spec):
    """Rows for the sealed access-links page (post-divider; names the stops)."""
    srcs = _sources(spec)
    ms = spec.get("map", {}).get("stops", [])
    out = []
    for i, st, kind in gated(spec):
        rec = st.get("access", {})
        src = srcs.get(rec.get("source"), {})
        name = ms[i - 1].get("answer_name") if i - 1 < len(ms) else None
        out.append({"stop": i, "name": name or st.get("answer", {}).get("name", ""),
                    "kind": KIND_LABEL[kind], "entry": rec.get("entry"),
                    "summary": rec.get("summary", ""), "fallback": rec.get("fallback", ""),
                    "url": src.get("url", ""), "publisher": src.get("publisher", ""),
                    "checked": nice_date(src.get("accessed"))})
    return out
