# -*- coding: utf-8 -*-
"""Print the cold-solver packet: everything a reader sees before the spoiler divider that bears on
the riddles, and nothing from after it. Hand the output to a reader who has not seen the spec or
the answers; they fill in cold_solver.json (skeleton written beside the spec with --skeleton).

    python riddle_pages.py <spec.py>              # print the packet
    python riddle_pages.py <spec.py> --skeleton   # also write cold_solver.json to fill in
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import riddles  # noqa: E402


def load_spec(path):
    ns = {}
    with open(path, encoding="utf-8") as f:
        exec(compile(f.read(), path, "exec"), ns)
    return ns["SPEC"]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    path = os.path.abspath(sys.argv[1])
    spec = load_spec(path)
    spec_dir = os.path.dirname(path)
    print(riddles.packet_text(spec, spec_dir))
    if "--skeleton" in sys.argv:
        sk = {"riddles_sha256": riddles.riddles_hash(spec, spec_dir), "reader": "", "date": "",
              "results": {str(i): {"named": "", "basis": "", "line": ""}
                          for i in range(1, len(spec.get("stops", [])) + 1)},
              "intro_leak": ""}
        out = os.path.join(os.path.dirname(path), "cold_solver.json")
        with open(out, "w") as f:
            json.dump(sk, f, indent=2, ensure_ascii=False)
        print(f"\nskeleton written: {out}")


if __name__ == "__main__":
    main()
