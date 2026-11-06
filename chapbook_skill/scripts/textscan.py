# -*- coding: utf-8 -*-
"""Information timing in hand-written text (block E: E2, E3).

Every page is read at one moment of the hunt:

    pre-walk   cover, How to Play (with the Before you go box), trail map, acts, maker
    on site    riddle pages, hints page
    post-hunt  spoiler divider, answer pages, the treasure, sources and credits
    any time   access-links page (sealed, inside the back cover; read by choice)

Post-hunt text is read after the walker has left, so it may not ask them to do something at the stop. A sentence that opens with an instruction ("Look up", "Stand across the
street", "Before you look up, look down") or points at the spot ("standing here", "in front of
you", "before you leave") blocks the build, unless it is written for a return visit ("Next time
you pass, count the lamps"). Write "What to notice" as what the walker saw, or as something to
look for next time.

An answer page, or the closing, may carry `timing_override: "<reason>"`; the override prints in
the build record as a warning.
"""

import re


class TextError(Exception):
    pass


# ------------------------------------------------------------------ timing

_IMP = (r"(?:look|stand|count|find|walk|turn|step|touch|go|check|read|listen|stop|search|spot|"
        r"climb|cross|face|head|peer|crouch|kneel|tilt|trace|note|notice|compare|glance|pause|"
        r"lean|follow|watch|try|take|photograph|circle|stoop|squint|run|feel)")
ON_SITE = [
    r"^\W*" + _IMP + r"\b",                                                  # imperative opening
    r"^\W*(?:before|while|as|once|when)\b[^,;:]{0,60}[,;:]\s*" + _IMP + r"\b",  # "Before you X, look"
    r"\bstanding here\b", r"\bfrom where you stand\b", r"\bin front of you\b",
    r"\byou are about to\b", r"\bbefore you (?:leave|go|move on)\b",
    r"\bwhile you(?:'re|’re| are) (?:here|there)\b", r"\bnow that you(?:'re|’re| are)\b",
    r"\bon your way (?:out|to)\b", r"\bas you leave\b", r"\bright now\b", r"\bfrom here\b",
]
NEXT_VISIT = (r"\b(?:next time|return visit|another visit|another day|"
              r"(?:when|if) you (?:go|come) back|on a (?:second|later|return) visit)\b")


def _text(x):
    return x["text"] if isinstance(x, dict) else x


def sentences(t):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|:\s+(?=[A-Z])", t or "") if s.strip()]


def post_hunt_texts(spec):
    """(where, text, override) for every hand-written string read after the hunt."""
    out = []
    for i, st in enumerate(spec.get("stops", []), 1):
        a = st.get("answer", {})
        ov = a.get("timing_override")
        for k, p in enumerate(a.get("paras", []), 1):
            out.append((f"answer {i} para {k}", _text(p), ov))
        for b in a.get("blocks", []):
            out.append((f"answer {i} block '{b[0]}'", b[1], ov))
        if "notice" in a:
            out.append((f"answer {i} '{a['notice'][0]}'", a["notice"][1], ov))
    c = spec.get("closing", {})
    ov = c.get("timing_override")
    for k, p in enumerate(c.get("paras", []), 1):
        out.append((f"closing para {k}", _text(p), ov))
    if c.get("pullquote"):
        out.append(("closing pullquote", c["pullquote"], ov))
    return out


def on_site_hit(sentence):
    """The matched phrase if the sentence asks for something at the stop, else None."""
    if re.search(NEXT_VISIT, sentence, re.I):
        return None
    for pat in ON_SITE:
        m = re.search(pat, sentence, re.I)
        if m:
            return m.group(0).strip(" ,;:")
    return None


def scan_timing(spec):
    """Returns (errors, warnings, report)."""
    errors, warnings, hits = [], [], []
    for where, t, ov in post_hunt_texts(spec):
        for s in sentences(t):
            h = on_site_hit(s)
            if not h:
                continue
            hits.append({"where": where, "sentence": s, "phrase": h, "override": ov})
            if ov:
                warnings.append(f"timing override at {where}: {ov}")
            else:
                errors.append(f"{where}: '{s[:90]}{'…' if len(s) > 90 else ''}' asks for something at "
                              f"the stop ('{h}'), but this page is read after the hunt; write it as what "
                              f"the walker saw, or for a return visit ('Next time you pass, …')")
    return errors, sorted(set(warnings)), {"post_hunt_sentences_flagged": hits}
