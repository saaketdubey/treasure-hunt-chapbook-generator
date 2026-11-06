#!/usr/bin/env python3
"""Render a standalone trail-map test page from a map spec module.

Usage:
    python scripts/build_map.py <map_spec.py> [out.pdf]

The spec module defines SPEC with `slug`, `title_line1`, `subtitle`, `palette`,
`display_font`, optional `draft_label`, and a schema-v2 `map`. Data paths in the
map resolve from the spec file's directory. Writes the PDF (one or two map pages) and a
`<out>_record.json` reproducibility record (generator version, code and spec
hashes, data manifest check, validation report). Exits 1 if the map is blocked.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    spec_path = os.path.abspath(sys.argv[1])
    spec_dir = os.path.dirname(spec_path)
    import engine
    import mapgen
    engine.SPEC_DIR = spec_dir
    ms = importlib.util.spec_from_file_location("map_spec", spec_path)
    mod = importlib.util.module_from_spec(ms)
    ms.loader.exec_module(mod)
    SPEC = mod.SPEC
    out = (os.path.abspath(sys.argv[2]) if len(sys.argv) > 2
           else os.path.join(spec_dir, SPEC["slug"] + ".pdf"))
    try:
        book = engine.Book(SPEC, out)
        pages = book.map_only()
    except mapgen.MapError as e:
        print(f"!! {e}")
        if os.path.exists(out):
            os.remove(out)
        return 1
    rec = mapgen.record(out, book.map_model, spec_path,
                        [os.path.join(HERE, f) for f in ("engine.py", "mapgen.py", "build_map.py")])
    print(f"{out}: {pages} page{'s' if pages != 1 else ''}")
    print(f"record: {rec}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
