#!/usr/bin/env python3
"""Fetch and cache OpenStreetMap source data for a chapbook map.

Usage:
    python scripts/fetch_osm.py <data-dir> <min_lon,min_lat,max_lon,max_lat> [relation_id ...]

Downloads the bounding box from the OpenStreetMap editing API (complete ways,
partial relations; boxes over the API's node limit are split into tiles), plus the full geometry of any listed relations (large
riverbank or park multipolygons whose members leave the box). Each response is
stored gzipped in <data-dir>, and <data-dir>/manifest.json records the exact URL,
fetch time (UTC), byte size and SHA-256 of every file.

Rendering never fetches. A map is reproducible from the cached files and the
manifest. Re-fetching produces a new data snapshot; record it as a new test.

Data © OpenStreetMap contributors, ODbL 1.0. Attribution is printed on the map.
"""
import datetime
import gzip
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.openstreetmap.org/api/0.6"
UA = "chapbook-generator/2.0 (map test fixture)"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    out_dir = os.path.abspath(sys.argv[1])
    bbox = sys.argv[2]
    rels = sys.argv[3:]
    os.makedirs(out_dir, exist_ok=True)
    jobs = [(f"relation_{r}.osm.gz", f"{API}/relation/{r}/full") for r in rels]
    manifest = {"source": "OpenStreetMap", "licence": "ODbL 1.0",
                "attribution": "© OpenStreetMap contributors",
                "copyright_url": "https://www.openstreetmap.org/copyright",
                "bbox": bbox, "files": []}
    def fetch_box(b, name):
        """The API refuses boxes over 50,000 nodes; split such a box in four and retry."""
        url = f"{API}/map?bbox={','.join(f'{v:.6f}' for v in b)}"
        try:
            return [(name, url, get(url))]
        except urllib.error.HTTPError as e:
            if e.code != 400:
                raise
        x0, y0, x1, y1 = b
        xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
        out = []
        for k, q in enumerate([(x0, y0, xm, ym), (xm, y0, x1, ym), (x0, ym, xm, y1), (xm, ym, x1, y1)]):
            out += fetch_box(q, name.replace(".osm.gz", f"_{k}.osm.gz"))
        return out

    fetched = fetch_box(tuple(float(v) for v in bbox.split(",")), "bbox.osm.gz")
    fetched += [(name, url, get(url)) for name, url in jobs]
    for name, url, raw in fetched:
        if not raw.lstrip().startswith(b"<?xml"):
            raise SystemExit(f"!! fetch failed for {url}: not OSM XML")
        path = os.path.join(out_dir, name)
        with open(path, "wb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0) as f:
            f.write(raw)
        manifest["files"].append({
            "file": name, "url": url,
            "fetched_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "bytes_uncompressed": len(raw),
            "sha256_uncompressed": hashlib.sha256(raw).hexdigest(),
        })
        print(f"{name}: {len(raw)} bytes")
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
