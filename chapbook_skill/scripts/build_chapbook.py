#!/usr/bin/env python3
"""Render a chapbook PDF from a spec module.

Usage:
    python scripts/build_chapbook.py <spec.py> [out.pdf]

Images referenced by answer pages are resolved from an `img/` directory next to
the spec file. Fonts come from the skill's own assets/fonts.
Prints the final page count, always a multiple of 4.
"""
import importlib.util
import os
import re
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
    engine.IMG_DIR = os.path.join(spec_dir, "img")
    engine.SPEC_DIR = spec_dir

    mod_spec = importlib.util.spec_from_file_location("chapbook_spec", spec_path)
    mod = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(mod)
    SPEC = mod.SPEC

    if len(sys.argv) > 2:
        out = os.path.abspath(sys.argv[2])
    else:
        title = f"{SPEC['title_line1']} {SPEC.get('title_line2', '')}: {SPEC['subtitle']}"
        safe = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-")
        out = os.path.join(spec_dir, safe + ".pdf")

    pages = engine.Book(SPEC, out).build()
    print(f"{out}: {pages} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
