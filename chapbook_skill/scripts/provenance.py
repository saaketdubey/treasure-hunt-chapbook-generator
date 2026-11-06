"""
Provenance for a chapbook spec: sources, images and the claim-to-source ledger.

The spec carries two record lists, `sources` and `images`, and every claim-bearing text
item may be written as `{"text": str, "sources": [source_id, ...]}` instead of a bare
string. This module:

  * validates the records and the ledger before anything is drawn (blocking errors);
  * reads `provenance_check.json`, written by `scripts/verify_provenance.py`, and blocks
    on failed live checks unless the record carries an `override` reason;
  * generates the credits-page lines from the records, so credits are never hand-typed;
  * writes the ledger into the build record so every claim can be traced after the fact.

Severities (backlog H, decision 5):
  blocking           — structural: missing fields, bad URL syntax, unknown or uncited source,
                       answer text with no source, image with no record or no file.
  blocking+override  — live: URL unreachable, Commons licence or author differs from the
                       record, local file not the Commons original. A record-level
                       `override` string with the reason lets the build continue; the
                       override is printed and recorded.
  human              — whether a source actually supports its claim. Never automated;
                       listed under `unperformed_checks` in the record.
"""
import datetime
import hashlib
import json
import os
import re

ALLOWED_LICENCES = {
    "CC0 1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "Public domain": None,
    "CC BY 2.0": "https://creativecommons.org/licenses/by/2.0/",
    "CC BY 2.5": "https://creativecommons.org/licenses/by/2.5/",
    "CC BY 3.0": "https://creativecommons.org/licenses/by/3.0/",
    "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC BY-SA 2.0": "https://creativecommons.org/licenses/by-sa/2.0/",
    "CC BY-SA 2.5": "https://creativecommons.org/licenses/by-sa/2.5/",
    "CC BY-SA 3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
    "CC BY-SA 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
}

URL_RE = re.compile(r"^https?://[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/[^\s]*)?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^[a-z0-9_]+$")

SOURCE_REQUIRED = ("id", "url", "title", "publisher", "accessed", "supports")
IMAGE_REQUIRED = ("id", "file", "page_url", "author", "licence", "checked")


class ProvenanceError(Exception):
    pass


# ---------------------------------------------------------------- claim items

def text_of(item):
    """A claim-bearing item is a str or {"text", "sources"}. Return its text."""
    if isinstance(item, dict):
        return item["text"]
    return item


def sources_of(item):
    if isinstance(item, dict):
        return list(item.get("sources", []))
    return []


def block_parts(block):
    """Answer blocks are (heading, text) or (heading, text, [source_ids])."""
    if len(block) == 3:
        return block[0], block[1], list(block[2])
    return block[0], block[1], []


# ---------------------------------------------------------------- ledger

def collect_claims(spec):
    """Every claim-bearing item in the spec with its location, text, source ids and
    whether a source is required there."""
    claims = []

    def add(where, item, required):
        claims.append({"where": where, "text": text_of(item),
                       "sources": sources_of(item), "required": required})

    for k, it in enumerate(spec.get("acts", {}).get("items", [])):
        if "text" in it:
            add(f"acts.items[{k}].text", it["text"], False)
    mk = spec.get("maker", {})
    for k, p in enumerate(mk.get("paras", [])):
        add(f"maker.paras[{k}]", p, False)
    for k, f in enumerate(mk.get("facts", [])):
        # (label, value) or (label, value, [ids])
        item = {"text": f"{f[0]}: {f[1]}", "sources": list(f[2]) if len(f) > 2 else []}
        add(f"maker.facts[{k}]", item, False)
    for n, st in enumerate(spec.get("stops", []), 1):
        r, a = st["riddle"], st["answer"]
        acc = st.get("access")
        if isinstance(acc, dict):
            # block E: the access summary is a changeable fact; its official page is the source
            add(f"stops[{n}].access",
                {"text": f"{acc.get('summary', '')} If shut: {acc.get('fallback', '')}",
                 "sources": [acc["source"]] if acc.get("source") else []}, True)
        if "hint" in r:
            add(f"stops[{n}].riddle.hint", r["hint"], False)
        for k, p in enumerate(a.get("paras", [])):
            add(f"stops[{n}].answer.paras[{k}]", p, True)
        for k, b in enumerate(a.get("blocks", [])):
            h, t, ids = block_parts(b)
            add(f"stops[{n}].answer.blocks[{k}]", {"text": f"{h}: {t}", "sources": ids}, True)
        if "notice" in a:
            h, t, ids = block_parts(a["notice"])
            add(f"stops[{n}].answer.notice", {"text": f"{h}: {t}", "sources": ids}, False)
    return claims


# ---------------------------------------------------------------- validation

def validate(spec, spec_dir, img_dir):
    """Structural checks. Returns (errors, warnings, ledger)."""
    errors, warnings = [], []
    sources = spec.get("sources")
    images = spec.get("images")
    if sources is None:
        errors.append("spec has no `sources` list (schema v3 provenance)")
        sources = []
    if images is None:
        errors.append("spec has no `images` list (schema v3 provenance)")
        images = []
    cr = spec.get("credits", {})
    for retired in ("images", "sources"):
        if retired in cr:
            errors.append(f"credits.{retired} is hand-written; retired — credits are generated "
                          f"from the `sources` and `images` records")

    sids = {}
    for k, s in enumerate(sources):
        where = f"sources[{k}]"
        for f in SOURCE_REQUIRED:
            if not s.get(f):
                errors.append(f"{where}: missing `{f}`")
        sid = s.get("id", "")
        if sid:
            if not ID_RE.match(sid):
                errors.append(f"{where}: id `{sid}` must be lowercase letters, digits, underscores")
            if sid in sids:
                errors.append(f"{where}: duplicate source id `{sid}`")
            sids[sid] = s
        if s.get("url") and not URL_RE.match(s["url"]):
            errors.append(f"{where}: `url` is not a full http(s) URL: {s['url']}")
        if s.get("accessed") and not DATE_RE.match(s["accessed"]):
            errors.append(f"{where}: `accessed` must be YYYY-MM-DD")
        if s.get("verified") is not True and not s.get("override"):
            errors.append(f"{where} ({sid}): `verified` is not True — fetch and read the source, "
                          f"then set verified: True, or give an `override` reason")
        if s.get("weaker_claim"):
            warnings.append(f"{where} ({sid}): weaker claim recorded — {s['weaker_claim']}")

    iids = {}
    files_seen = {}
    for k, im in enumerate(images):
        where = f"images[{k}]"
        for f in IMAGE_REQUIRED:
            if not im.get(f):
                errors.append(f"{where}: missing `{f}`")
        iid = im.get("id", "")
        if iid:
            if not ID_RE.match(iid):
                errors.append(f"{where}: id `{iid}` must be lowercase letters, digits, underscores")
            if iid in iids:
                errors.append(f"{where}: duplicate image id `{iid}`")
            iids[iid] = im
        for uf in ("page_url", "file_url", "licence_url"):
            if im.get(uf) and not URL_RE.match(im[uf]):
                errors.append(f"{where}: `{uf}` is not a full http(s) URL: {im[uf]}")
        lic = im.get("licence")
        if lic and lic not in ALLOWED_LICENCES:
            errors.append(f"{where}: licence `{lic}` is not in the accepted list "
                          f"({', '.join(ALLOWED_LICENCES)})")
        elif lic and ALLOWED_LICENCES[lic]:
            if not im.get("licence_url"):
                im["licence_url"] = ALLOWED_LICENCES[lic]          # default from the licence name
            elif im["licence_url"].rstrip("/") != ALLOWED_LICENCES[lic].rstrip("/"):
                errors.append(f"{where}: `licence_url` must be {ALLOWED_LICENCES[lic]} for {lic}")
        if im.get("checked") and not DATE_RE.match(im["checked"]):
            errors.append(f"{where}: `checked` must be YYYY-MM-DD")
        if im.get("verified") is not True and not im.get("override"):
            errors.append(f"{where} ({iid}): `verified` is not True — open the file page, confirm "
                          f"author and licence, then set verified: True, or give an `override` reason")
        fn = im.get("file")
        if fn:
            if fn in files_seen:
                errors.append(f"{where}: file `{fn}` also recorded by images[{files_seen[fn]}]")
            files_seen[fn] = k
            if not os.path.exists(os.path.join(img_dir, fn)):
                errors.append(f"{where}: file `{fn}` not found in {img_dir}")

    # every answer image has a record
    for n, st in enumerate(spec.get("stops", []), 1):
        a = st["answer"]
        if "credit" in a:
            errors.append(f"stops[{n}].answer.credit is hand-written; retired — the credit line is "
                          f"generated from the image record")
        fn = a.get("image")
        if fn and fn not in files_seen:
            errors.append(f"stops[{n}].answer.image `{fn}` has no record in `images`")

    # ledger
    ledger = collect_claims(spec)
    cited = set()
    for c in ledger:
        for sid in c["sources"]:
            cited.add(sid)
            if sid not in sids:
                errors.append(f"{c['where']}: unknown source id `{sid}`")
        if c["required"] and not c["sources"]:
            errors.append(f"{c['where']}: answer text with no source — write it as "
                          f"{{\"text\": ..., \"sources\": [...]}}")
    for sid in sids:
        if sid not in cited:
            errors.append(f"sources `{sid}` is never cited by any claim")

    return errors, warnings, ledger


# ---------------------------------------------------------------- live checks

def load_live_checks(spec, spec_dir):
    """Read provenance_check.json (from verify_provenance.py). Returns (errors, warnings,
    report). Missing file is blocking unless spec["provenance"]["skip_live_checks"] gives
    a reason."""
    errors, warnings = [], []
    path = os.path.join(spec_dir, "provenance_check.json")
    skip = spec.get("provenance", {}).get("skip_live_checks")
    if not os.path.exists(path):
        if skip:
            warnings.append(f"live provenance checks skipped: {skip}")
            return errors, warnings, {"performed": False, "reason": skip}
        errors.append("provenance_check.json not found — run scripts/verify_provenance.py "
                      "<spec.py> first, or set provenance.skip_live_checks with a reason")
        return errors, warnings, {"performed": False}
    rep = json.load(open(path))
    by_id = {}
    for s in spec.get("sources", []):
        by_id[("source", s.get("id"))] = s
    for im in spec.get("images", []):
        by_id[("image", im.get("id"))] = im
    # stale check: spec records changed since the check ran
    if rep.get("records_sha256") != records_hash(spec):
        errors.append("provenance_check.json is stale — the `sources`/`images` records changed "
                      "after verify_provenance.py ran; run it again")
    for r in rep.get("results", []):
        key = (r["kind"], r["id"])
        rec = by_id.get(key, {})
        if r["status"] == "ok":
            continue
        msg = f"{r['kind']} `{r['id']}`: {r['status']} — {r.get('detail', '')}"
        if rec.get("override"):
            warnings.append(f"OVERRIDE {msg} | reason: {rec['override']}")
        else:
            errors.append(msg + " (add an `override` reason to the record to proceed)")
    return errors, warnings, rep


def records_hash(spec):
    blob = json.dumps({"sources": spec.get("sources", []), "images": spec.get("images", [])},
                      sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


# ---------------------------------------------------------------- generated text

def image_record_for(spec, filename):
    for im in spec.get("images", []):
        if im.get("file") == filename:
            return im
    return None


def credit_line(im):
    """The one-line credit printed under an answer-page photograph."""
    parts = [f"Photograph: {im['author']}", im["licence"]]
    if im.get("attribution"):
        parts.append(im["attribution"])
    if im.get("modified"):
        parts.append(im["modified"])
    return ". ".join(parts) + "."


def credits_image_lines(spec):
    lines = []
    for n, st in enumerate(spec.get("stops", []), 1):
        a = st["answer"]
        im = image_record_for(spec, a.get("image"))
        if not im:
            continue
        bits = [f"Stop {n} — {im.get('caption') or a['name']}", f"Photograph: {im['author']}",
                im["licence"]]
        if im.get("attribution"):
            bits.append(im["attribution"])
        if im.get("modified"):
            bits.append(im["modified"])
        lines.append(". ".join(bits) + ". " + strip_scheme(im["page_url"]))
    return lines


def credits_source_lines(spec):
    lines = []
    for k, s in enumerate(spec.get("sources", []), 1):
        pub = s["publisher"]
        title = s["title"]
        head = title if pub.lower() in title.lower() else f"{title}, {pub}"
        line = f"{k}. {head}. {strip_scheme(s['url'])} — {s['supports']}"
        if s.get("weaker_claim"):
            line += f" Note: {s['weaker_claim']}"
        lines.append(line)
    return lines


def strip_scheme(url):
    return re.sub(r"^https?://", "", url)


# ---------------------------------------------------------------- record

def build_record(spec, spec_path, out_pdf, ledger, warnings, live_report, errors=None, riddles=None,
                 access=None, timing=None):
    def h(p):
        return hashlib.sha256(open(p, "rb").read()).hexdigest() if p and os.path.exists(p) else None
    rec = {
        "schema": "chapbook spec v3 (provenance)",
        "built": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "spec": {"path": os.path.basename(spec_path), "sha256": h(spec_path)},
        "output": {"pdf": os.path.basename(out_pdf), "sha256": h(out_pdf)},
        "status": "draft — pending author review",
        "errors": errors or [],
        "warnings": warnings,
        "sources": spec.get("sources", []),
        "images": spec.get("images", []),
        "ledger": ledger,
        "live_checks": live_report,
        "riddles": riddles,
        "access": access,
        "timing": timing,
        "automated_checks": [
            "record fields present, ids well formed and unique",
            "URL syntax on every source and image URL",
            "image licence in the accepted list; licence URL matches",
            "every answer paragraph and block cites at least one known source",
            "every source is cited at least once",
            "every answer image has a record and a file on disk",
            "hand-written credits and credit lines refused",
            "live-check report present and not stale (see live_checks)",
            "access records: gated stops carry entry, summary, fallback and an official source; "
            "optional entry has public evidence only; required-entry stops last; How to Play "
            "text free of tickets, hours, prices and 'free'; checked date not stale (warns)",
            "information timing: post-hunt text (answers, treasure) asks for nothing at the stop "
            "unless written for a return visit",
        ],
        "unperformed_checks": [
            "whether each source actually supports the claim it is cited for (human: read the "
            "source against the text)",
            "whether the photograph shows the thing the answer names (human: compare image to "
            "its Commons page and to the stop)",
            "whether a weaker-claim note changed the prose as it should have (human)",
            "whether each access summary still matches its official page on the day of the "
            "walk (human: re-read the page before printing)",
            "whether post-hunt text the timing scan passed still reads as looking back (human: "
            "the scan matches phrasing, not meaning)",
        ],
    }
    path = os.path.splitext(out_pdf)[0] + "_record.json"
    with open(path, "w") as f:
        json.dump(rec, f, indent=2, ensure_ascii=False, default=str)
    return path
