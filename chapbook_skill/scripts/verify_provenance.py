#!/usr/bin/env python3
"""Live provenance checks for a chapbook spec. Run before build_chapbook.py.

Usage:
    python scripts/verify_provenance.py <spec.py>

For every record in SPEC["sources"]: fetch the URL (GET, 20 s timeout) and record the
HTTP status. For every record in SPEC["images"] whose page_url is a Wikimedia Commons file
page: ask the Commons API for the file's author, licence and SHA-1, compare them with the
record, and compare the SHA-1 with the local file in img/. Anything else is reported as
`unchecked` so a human can do it.

Writes provenance_check.json next to the spec. The engine refuses to build without it,
blocks on any non-ok result that has no `override` reason in its record, and refuses a
stale report if the records changed after this ran.

This script checks reachability and identity. It does not and cannot check that a source
supports the claim it is cited for; that is the author's reading.
"""
import datetime
import hashlib
import importlib.util
import json
import os
import re
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import provenance  # noqa: E402

UA = "chapbook-provenance-check/1.0 (walking-riddle chapbook generator; verify_provenance.py)"
COMMONS_RE = re.compile(r"^https?://commons\.wikimedia\.org/wiki/(File:.+)$")

# Commons LicenseShortName values that map onto the record's licence string.
LICENCE_ALIASES = {
    "CC0": "CC0 1.0", "CC0 1.0": "CC0 1.0",
    "Public domain": "Public domain", "PD": "Public domain",
    "CC BY 2.0": "CC BY 2.0", "CC BY 2.5": "CC BY 2.5", "CC BY 3.0": "CC BY 3.0", "CC BY 4.0": "CC BY 4.0",
    "CC BY-SA 2.0": "CC BY-SA 2.0", "CC BY-SA 2.5": "CC BY-SA 2.5",
    "CC BY-SA 3.0": "CC BY-SA 3.0", "CC BY-SA 4.0": "CC BY-SA 4.0",
}


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def check_source(s):
    try:
        status, _ = fetch(s["url"])
    except Exception as e:  # noqa: BLE001
        code = getattr(e, "code", None)
        return {"kind": "source", "id": s["id"], "status": "unreachable",
                "detail": f"HTTP {code}" if code else str(e)[:160]}
    if status != 200:
        return {"kind": "source", "id": s["id"], "status": "unreachable", "detail": f"HTTP {status}"}
    return {"kind": "source", "id": s["id"], "status": "ok", "detail": "HTTP 200"}


def check_image(im, img_dir):
    out = {"kind": "image", "id": im["id"]}
    m = COMMONS_RE.match(im.get("page_url", ""))
    if not m:
        out.update(status="unchecked", detail="not a Wikimedia Commons file page; verify by hand")
        return out
    title = urllib.parse.unquote(m.group(1))
    api = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo"
           "&iiprop=extmetadata|url|sha1&titles=" + urllib.parse.quote(title))
    try:
        _, body = fetch(api)
        pages = json.loads(body)["query"]["pages"]
        info = next(iter(pages.values()))["imageinfo"][0]
    except Exception as e:  # noqa: BLE001
        out.update(status="unreachable", detail=f"Commons API: {str(e)[:160]}")
        return out
    meta = info.get("extmetadata", {})
    author = strip_html(meta.get("Artist", {}).get("value"))
    lic_short = strip_html(meta.get("LicenseShortName", {}).get("value"))
    lic = LICENCE_ALIASES.get(lic_short, lic_short)
    problems = []
    found = {"author": author, "licence": lic_short, "sha1": info.get("sha1"),
             "url": (info.get("url") or "").split("?")[0]}
    if im.get("author") and im["author"].lower() not in author.lower():
        problems.append(f"author on Commons is '{author}', record says '{im['author']}'")
    if im.get("licence") and lic != im["licence"]:
        problems.append(f"licence on Commons is '{lic_short}', record says '{im['licence']}'")
    local = os.path.join(img_dir, im.get("file", ""))
    if os.path.exists(local):
        sha1 = hashlib.sha1(open(local, "rb").read()).hexdigest()
        found["local_sha1"] = sha1
        if info.get("sha1") and sha1 != info["sha1"]:
            if im.get("modified"):
                found["note"] = "local file differs from the Commons original; record declares a modification"
            else:
                problems.append("local file is not the Commons original (SHA-1 differs) and the record "
                                "declares no modification")
    else:
        problems.append("local file missing")
    commons_url = (info.get("url") or "").split("?")[0]
    if im.get("file_url") and commons_url and im["file_url"] != commons_url:
        problems.append(f"file_url differs from Commons original URL {commons_url}")
    out["found"] = found
    if problems:
        out.update(status="mismatch", detail="; ".join(problems))
    elif found.get("note"):
        out.update(status="ok", detail="author and licence match Commons; local file is a declared "
                                       "modification of the original")
    else:
        out.update(status="ok", detail="author, licence and file hash match Commons")
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    spec_path = os.path.abspath(sys.argv[1])
    spec_dir = os.path.dirname(spec_path)
    ms = importlib.util.spec_from_file_location("chapbook_spec", spec_path)
    mod = importlib.util.module_from_spec(ms)
    ms.loader.exec_module(mod)
    spec = mod.SPEC
    img_dir = os.path.join(spec_dir, "img")

    results = []
    for s in spec.get("sources", []):
        r = check_source(s)
        results.append(r)
        print(f"  source {r['id']:24s} {r['status']:12s} {r['detail']}")
    for im in spec.get("images", []):
        r = check_image(im, img_dir)
        results.append(r)
        print(f"  image  {r['id']:24s} {r['status']:12s} {r['detail']}")

    rep = {
        "checked": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "spec": os.path.basename(spec_path),
        "records_sha256": provenance.records_hash(spec),
        "results": results,
        "not_checked": ["whether each source supports its claim", "image content versus the stop"],
    }
    out = os.path.join(spec_dir, "provenance_check.json")
    with open(out, "w") as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)
    bad = [r for r in results if r["status"] not in ("ok", "unchecked")]
    print(f"{out}: {len(results)} records, {len(bad)} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
