"""
Chapbook engine — a reusable print-ready layout system for city walking-hunt chapbooks.

Design lineage: "Cellini's Florence: A Five-Stop Renaissance Treasure Hunt".
Page size 5.5 x 8.5 in portrait, safe margins >= 0.39in, saddle-stitch friendly
(page count must be a multiple of 4).

A chapbook is described entirely by a SPEC dict (see spec_*.py) and rendered here.
"""
import os
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import inch
from reportlab.lib.colors import Color, HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

HERE = os.path.dirname(os.path.abspath(__file__))
# Asset roots. FONT_DIR ships with the skill; IMG_DIR is the working project
# directory and is overridden by build_chapbook.py.
FONT_DIR = os.path.join(os.path.dirname(HERE), "assets", "fonts")
IMG_DIR = os.path.join(os.getcwd(), "img")
SPEC_DIR = os.getcwd()   # map data paths resolve from here; set by the build scripts
PW, PH = 5.5 * inch, 8.5 * inch
M = 0.52 * inch          # content margin (> 0.39in ink-safe requirement)
FRAME = 0.34 * inch      # decorative frame inset

# ---------------------------------------------------------------- fonts

def register_fonts():
    fonts = {
        "Cormorant": "Cormorant.ttf",
        "Cormorant-Italic": "CormorantItalic.ttf",
        "Garamond": "EBGaramond.ttf",
        "Garamond-Italic": "EBGaramondItalic.ttf",
        "Body": "SourceSerif.ttf",
        "Body-Italic": "SourceSerifItalic.ttf",
    }
    for name, fn in fonts.items():
        path = os.path.join(FONT_DIR, fn)
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(name, path))


# ---------------------------------------------------------------- helpers

def tint(c, f):
    """Blend colour c toward white by factor f (0 = c, 1 = white)."""
    return Color(c.red + (1 - c.red) * f, c.green + (1 - c.green) * f,
                 c.blue + (1 - c.blue) * f)


class Book:
    def __init__(self, spec, out_path):
        register_fonts()
        self.s = spec
        self.p = {k: HexColor(v) for k, v in spec["palette"].items()}
        self.display = spec.get("display_font", "Cormorant")
        self.display_i = self.display + "-Italic"
        self.c = rl_canvas.Canvas(out_path, pagesize=(PW, PH))
        self.c.setTitle(spec["title_line1"] + ": " + spec["subtitle"])
        self.c.setAuthor(spec.get("author", "Chapbook Engine"))
        self.page_no = 0

    # ---- primitives -------------------------------------------------

    def text_width(self, s, font, size):
        return pdfmetrics.stringWidth(s, font, size)

    def centered(self, y, s, font, size, color=None, tracking=0):
        c = self.c
        c.setFont(font, size)
        c.setFillColor(color or self.p["ink"])
        if tracking:
            w = self.text_width(s, font, size) + tracking * (len(s) - 1)
            x = (PW - w) / 2
            for ch in s:
                c.drawString(x, y, ch)
                x += self.text_width(ch, font, size) + tracking
        else:
            c.drawCentredString(PW / 2, y, s)

    def left(self, x, y, s, font, size, color=None, tracking=0):
        c = self.c
        c.setFont(font, size)
        c.setFillColor(color or self.p["ink"])
        if tracking:
            for ch in s:
                c.drawString(x, y, ch)
                x += self.text_width(ch, font, size) + tracking
        else:
            c.drawString(x, y, s)

    def wrap(self, s, font, size, width):
        lines, cur = [], ""
        for w in s.split():
            # hard-break tokens (long URLs) that cannot fit on a line at all
            while self.text_width(w, font, size) > width:
                lo, hi = 1, len(w)
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    if self.text_width(w[:mid], font, size) <= width:
                        lo = mid
                    else:
                        hi = mid - 1
                head, w = w[:lo], w[lo:]
                if cur:
                    lines.append(cur)
                    cur = ""
                lines.append(head)
            t = (cur + " " + w).strip()
            if self.text_width(t, font, size) <= width:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def para(self, x, y, s, font, size, width, leading, color=None,
             align="left", first_indent=0):
        """Draw a wrapped paragraph. Returns the y after the last line."""
        c = self.c
        c.setFillColor(color or self.p["ink"])
        c.setFont(font, size)
        lines = self.wrap(s, font, size, width - first_indent)
        for i, ln in enumerate(lines):
            xx = x + (first_indent if i == 0 else 0)
            if align == "center":
                c.drawCentredString(x + width / 2, y, ln)
            elif align == "justify" and i < len(lines) - 1 and len(ln.split()) > 1:
                words = ln.split()
                tw = sum(self.text_width(w, font, size) for w in words)
                gap = (width - tw) / (len(words) - 1)
                cx = xx
                for w in words:
                    c.drawString(cx, y, w)
                    cx += self.text_width(w, font, size) + gap
            else:
                c.drawString(xx, y, ln)
            y -= leading
        return y + leading

    def para_height(self, s, font, size, width, leading):
        return len(self.wrap(s, font, size, width)) * leading

    # ---- ornaments --------------------------------------------------

    def kicker(self, y, s, color=None, size=7.0):
        self.centered(y, s.upper(), "Body", size, color or self.p["accent2"], tracking=2.2)

    def diamond_rule(self, y, half=68, color=None, weight=0.7):
        c = self.c
        col = color or self.p["gold"]
        c.setStrokeColor(col)
        c.setLineWidth(weight)
        cx = PW / 2
        c.line(cx - half, y, cx - 10, y)
        c.line(cx + 10, y, cx + half, y)
        c.setFillColor(self.p["accent"])
        c.saveState()
        c.translate(cx, y)
        c.rotate(45)
        c.rect(-2.4, -2.4, 4.8, 4.8, stroke=0, fill=1)
        c.restoreState()

    def frame(self, heavy=False):
        c = self.c
        c.setStrokeColor(self.p["accent"] if heavy else tint(self.p["gold"], 0.25))
        c.setLineWidth(1.5 if heavy else 0.8)
        c.rect(FRAME, FRAME, PW - 2 * FRAME, PH - 2 * FRAME, stroke=1, fill=0)
        if heavy:
            c.setLineWidth(0.5)
            c.setStrokeColor(tint(self.p["accent"], 0.45))
            g = 4.5
            c.rect(FRAME + g, FRAME + g, PW - 2 * (FRAME + g), PH - 2 * (FRAME + g),
                   stroke=1, fill=0)

    def background(self):
        c = self.c
        c.setFillColor(self.p["paper"])
        c.rect(0, 0, PW, PH, stroke=0, fill=1)

    def folio(self):
        self.page_no += 1
        if self.page_no == 1:
            return
        y = FRAME - 11
        c = self.c
        s = str(self.page_no)
        c.setFont("Body", 7.6)
        c.setFillColor(self.p["accent2"])
        c.drawCentredString(PW / 2, y, s)
        w = self.text_width(s, "Body", 7.6)
        c.setFillColor(tint(self.p["gold"], 0.1))
        for dx in (-w / 2 - 9, w / 2 + 9):
            c.saveState()
            c.translate(PW / 2 + dx, y + 2.4)
            c.rotate(45)
            c.rect(-1.5, -1.5, 3, 3, stroke=0, fill=1)
            c.restoreState()

    def page_break(self):
        self.folio()
        self.c.showPage()

    # ---- shared page furniture --------------------------------------

    def page_head(self, kicker, title_lines, y_top=None, title_size=22.5):
        """Kicker + centred display title + diamond rule. Returns y below."""
        y = y_top if y_top is not None else PH - M - 28
        self.kicker(y, kicker)
        y -= 26
        from reportlab.pdfbase.pdfmetrics import stringWidth
        room = PW - 2 * M - 24
        widest = max(stringWidth(ln, self.display, title_size) for ln in title_lines)
        if widest > room:                       # shrink a long title to fit, never overflow
            title_size *= room / widest
        for ln in title_lines:
            self.centered(y, ln, self.display, title_size, self.p["accent"])
            y -= title_size * 1.12
        y += title_size * 0.22
        self.diamond_rule(y - 4)
        return y - 22

    def section_label(self, x, y, s, color=None):
        self.left(x, y, s.upper(), "Body", 6.9, color or self.p["accent2"], tracking=1.5)
        return y - 13

    # ================================================================
    # PAGES
    # ================================================================

    def cover(self):
        s = self.s
        self.background()
        self.frame(heavy=True)
        y = PH - 1.55 * inch
        self.kicker(y, s["cover_kicker"], self.p["accent2"], size=7.4)
        y -= 20
        self.diamond_rule(y, half=52)
        y -= 46
        for ln in (s["title_line1"], s.get("title_line2")):
            if not ln:
                continue
            self.centered(y, ln, self.display, 35, self.p["accent"])
            y -= 41
        y += 6
        c = self.c
        c.setStrokeColor(self.p["accent"])
        c.setLineWidth(1.6)
        c.line(M + 14, y, PW - M - 14, y)
        c.setLineWidth(0.6)
        c.line(M + 14, y - 3.6, PW - M - 14, y - 3.6)
        y -= 30
        for ln in s["subtitle_lines"]:
            self.centered(y, ln, self.display, 16.5, self.p["ink"])
            y -= 20
        y -= 8
        for ln in s["cover_tagline_lines"]:
            self.centered(y, ln, self.display_i, 11.2, self.p["accent2"])
            y -= 14
        # motif medallion
        self.motif(PW / 2, y - 76, 52, s.get("cover_motif", "arch"))
        y = M + 74
        self.diamond_rule(y, half=52)
        y -= 28
        c.setFont("Body", 9.4)
        c.setFillColor(self.p["ink"])
        for lab in ("For:", "Date:"):
            c.drawString(M + 24, y, lab)
            c.setStrokeColor(tint(self.p["gold"], 0.15))
            c.setLineWidth(0.6)
            c.line(M + 24 + 32, y - 2, PW - M - 24, y - 2)
            y -= 22
        self.page_break()

    def motif(self, cx, cy, r, kind):
        c = self.c
        c.saveState()
        c.setStrokeColor(self.p["accent"])
        c.setLineWidth(1.1)
        c.circle(cx, cy, r, stroke=1, fill=0)
        c.setStrokeColor(tint(self.p["gold"], 0.1))
        c.setLineWidth(0.6)
        c.circle(cx, cy, r - 5, stroke=1, fill=0)
        c.setFillColor(self.p["accent"])
        c.saveState()
        c.translate(cx, cy + r - 13)
        c.rotate(45)
        c.rect(-1.8, -1.8, 3.6, 3.6, stroke=0, fill=1)
        c.restoreState()
        g = self.p["gold"]
        c.setStrokeColor(g)
        c.setFillColor(g)
        if kind == "fountain":
            # a rising jet over a shell basin
            c.setLineWidth(1.3)
            p = c.beginPath()
            p.moveTo(cx, cy + 22)
            p.curveTo(cx - 7, cy + 8, cx - 5, cy - 2, cx, cy - 6)
            p.curveTo(cx + 5, cy - 2, cx + 7, cy + 8, cx, cy + 22)
            c.drawPath(p, stroke=1, fill=0)
            for dx in (-15, 15):
                p = c.beginPath()
                p.moveTo(cx + dx * 0.35, cy + 12)
                p.curveTo(cx + dx, cy + 6, cx + dx * 1.15, cy - 2, cx + dx * 0.9, cy - 6)
                c.drawPath(p, stroke=1, fill=0)
            c.setLineWidth(1.5)
            p = c.beginPath()
            p.moveTo(cx - 26, cy - 10)
            p.curveTo(cx - 20, cy - 26, cx + 20, cy - 26, cx + 26, cy - 10)
            c.drawPath(p, stroke=1, fill=0)
            c.setLineWidth(0.7)
            for dx in (-16, -8, 0, 8, 16):
                c.line(cx + dx, cy - 11.5, cx + dx * 0.82, cy - 22.5)
        elif kind == "crescent":
            # square, circle, crescent: the three Georgian shapes
            c.setLineWidth(1.2)
            c.rect(cx - 25, cy + 6, 22, 22, stroke=1, fill=0)
            c.circle(cx + 14, cy + 17, 11, stroke=1, fill=0)
            p = c.beginPath()
            p.moveTo(cx - 27, cy - 20)
            p.curveTo(cx - 16, cy - 2, cx + 16, cy - 2, cx + 27, cy - 20)
            c.drawPath(p, stroke=1, fill=0)
            c.setLineWidth(0.8)
            for i in range(9):
                x = cx - 24 + i * 6
                yt = cy - 20 + (1 - ((x - cx) / 27.0) ** 2) * 16
                c.line(x, cy - 20, x, yt)
        else:  # arch
            c.setLineWidth(1.2)
            for dx in (-17, 0, 17):
                c.line(cx + dx - 7, cy - 16, cx + dx - 7, cy + 4)
                c.line(cx + dx + 7, cy - 16, cx + dx + 7, cy + 4)
                p = c.beginPath()
                p.moveTo(cx + dx - 7, cy + 4)
                p.curveTo(cx + dx - 7, cy + 14, cx + dx + 7, cy + 14, cx + dx + 7, cy + 4)
                c.drawPath(p, stroke=1, fill=0)
            c.setLineWidth(1.4)
            c.line(cx - 28, cy + 17, cx + 28, cy + 17)
            c.line(cx - 28, cy - 17, cx + 28, cy - 17)
        c.restoreState()

    def how_to_play(self):
        s = self.s["how_to_play"]
        self.background()
        self.frame()
        y = self.page_head("Before you begin", ["How to Play"])
        x, W = M, PW - 2 * M
        y = self.para(x, y, s["intro"], "Body", 9.3, W, 13.4, align="justify") - 14
        # italic mechanic note in a tinted well
        h = self.para_height(s["mechanic"], self.display_i, 10.4, W - 34, 14.2)
        self.c.setFillColor(tint(self.p["accent2"], 0.9))
        self.c.rect(x + 8, y - h + 5, W - 16, h + 8, stroke=0, fill=1)
        y = self.para(x + 17, y, s["mechanic"], self.display_i, 10.4, W - 34, 14.2,
                      self.p["accent2"], align="center") - 17
        y = self.section_label(x, y, "At each stop")
        for i, step in enumerate(s["steps"], 1):
            self.left(x + 3, y, f"{i}.", "Body", 9.2, self.p["accent"])
            y = self.para(x + 19, y, step, "Body", 9.3, W - 19, 12.8) - 12.6
        y -= 3
        y = self.section_label(x, y, s["checklist_title"])
        c = self.c
        for item in s["checklist"]:
            c.setStrokeColor(self.p["accent2"])
            c.setLineWidth(0.7)
            c.rect(x + 4, y - 1.6, 7.6, 7.6, stroke=1, fill=0)
            self.left(x + 19, y, item, "Body", 9.2, self.p["ink"])
            y -= 14.2
        y -= 5
        y = self.section_label(x, y, "Practical notes")
        # adaptive sizing so the notes always clear the frame
        avail = y - (M + 10)
        ns, nl, ngap = 8.6, 11.8, 12.6
        for cand in (8.6, 8.4, 8.2, 8.0, 7.8, 7.6, 7.4, 7.2, 7.0):
            lead = cand * 1.38
            tot = sum(self.para_height(n, "Body", cand, W - 20, lead) + 1.2
                      for n in s["notes"])
            if tot <= avail:
                ns, nl, ngap = cand, lead, lead + 1.2
                break
        else:
            ns, nl, ngap = 7.0, 9.7, 10.9
        for note in s["notes"]:
            c.setFillColor(self.p["gold"])
            c.saveState()
            c.translate(x + 7, y + 3.2)
            c.rotate(45)
            c.rect(-1.7, -1.7, 3.4, 3.4, stroke=0, fill=1)
            c.restoreState()
            y = self.para(x + 17, y, note, "Body", ns, W - 20, nl) - ngap
        if y < M + 4:
            print("  !! how_to_play overflow, y =", round(y, 1))
        self.page_break()

    def trail_map(self):
        """Map page from map schema v2. Geometry, route, areas and labels come from
        mapgen; nothing on this page is positioned by hand."""
        import mapgen
        m = self.s["map"]
        if m.get("placeholder"):
            raise mapgen.MapError("map not written yet: build it from templates/map_spec_example.py, "
                                  "test it with scripts/build_map.py, and paste it into the book spec")
        if m.get("version") != 2:
            raise mapgen.MapError("map schema v2 required; the v1 hand-placed schematic "
                                  "schema is retired (see references/spec-schema.md)")
        model = mapgen.MapModel(m, SPEC_DIR, self.s.get("slug", "map"))
        x0 = M - 2
        w = PW - 2 * (M - 2)

        def plate_h(first, last, carry, cafe=None):
            """Map box height = what the page has left once the head and captions are measured."""
            from reportlab.pdfgen import canvas as _cv
            import io
            real = self.c
            self.c = _cv.Canvas(io.BytesIO(), pagesize=(PW, PH))
            try:
                y = self.page_head("Orientation", [m["title"] + (", continued" if not first else "")])
                here = bool(model.cafes) if cafe is None else cafe
                used = self._map_captions(model, x0, 1000.0, w, first=first, last=last, carry=carry,
                                          measure=True,
                                          cafes=[{"name": c["name"]} for c in model.cafes[:3]] if here else [])
            finally:
                self.c = real
            return (y - 6) - (M + 18) - used - 6

        h = plate_h(True, True, None)
        plan = model.plan_panels(w, h)        # one page, or two for a long route; decided up front
        rep = model.report
        debug = os.environ.get("CHAPBOOK_MAP_DEBUG") == "1"
        pages, layouts = [], []
        for pg, pnl in enumerate(plan, 1):
            sub = model.panel(pnl) if len(plan) > 1 else model
            if sub is model and pnl.get("radii"):
                model.areas = [model._grown_area(model.group[k], pnl["radii"][model.group[k]])
                               if model.group[k] in pnl["radii"] else a for k, a in enumerate(model.areas)]
            if sub is not model:
                sub.report["errors"] = []
            pages.append((pg, pnl, sub))
        if len(pages) > 1:
            # one scale-bar value on every page when it reads on all of them
            heights = {}
            for pg, pnl, sub in pages:
                carry = (pnl.get("carry") + 1) if pnl.get("carry") is not None else None
                heights[pg] = plate_h(pg == 1, pg == len(plan), carry, cafe=bool(sub.cafes))
            scales = [mapgen.layout_extent(sub, (x0, 0, w, heights[pg]))[4] for pg, _, sub in pages]
            shared = mapgen.shared_scale_value(scales, w, model.units)
            rep["scale_bar_shared"] = shared
            for i, (pg, _, sub) in enumerate(pages):
                sub.scale_value = shared
                sub.prev_scale = (scales[i - 1], pg - 1) if i else None
        for pg, pnl, sub in pages:
            self.background()
            self.frame()
            kick = "Orientation" if len(plan) == 1 else f"Orientation · {pg} of {len(plan)}"
            y = self.page_head(kick, [m["title"]])
            carry = (pnl.get("carry") + 1) if pnl.get("carry") is not None and len(plan) > 1 else None
            hp = h if len(plan) == 1 else plate_h(pg == 1, pg == len(plan), carry, cafe=bool(sub.cafes))
            y1 = y - 6
            y0 = y1 - hp
            lay = sub.layout((x0, y0, w, hp), self.text_width)
            if sub is not model:
                tag = f"page {pg}: "
                rep["errors"] += [tag + e for e in sub.report["errors"]]
                rep["warnings"] += [tag + e for e in sub.report["warnings"]]
                rep.setdefault("pages", []).append({k: v for k, v in sub.report.items()
                                                    if k not in ("errors", "warnings")})
            layouts.append(lay)
            if rep["errors"] and not debug:
                raise mapgen.MapError("map blocked:\n  " + "\n  ".join(rep["errors"]))
            if rep["errors"] and pg == 1:
                print("!! DEBUG render of a blocked map (not a deliverable):\n  " + "\n  ".join(rep["errors"]))
            mapgen.draw(self, lay)
            self._map_captions(model, x0, y0, w, last=(pg == len(pages)), first=(pg == 1), carry=carry,
                               cafes=getattr(lay, "cafes_placed", []))
        self.map_model, self.map_layout = model, layouts[0]
        for wmsg in rep["warnings"]:
            print("!! map warning:", wmsg)

    def _map_captions(self, model, x0, y0, w, first, last, carry=None, measure=False, cafes=()):
        import mapgen
        # legend: only what is drawn, measured, never shrunk
        ly = y0 - 14
        items = [("route", "Walking route"), ("area", "Numbered stop"), ("bldg", "Landmark")]
        if cafes:
            items.append(("cafe", "Café break"))
        widths = [16 + self.text_width(t, "Body", 6.6) + 10 for _, t in items]
        total = sum(widths) - 10
        if total > w:
            raise mapgen.MapError(f"map legend overflows the plate ({total:.0f} > {w:.0f} pt)")
        xx = x0 + (w - total) / 2
        c = self.c
        for (kind, label), ww in zip(items, widths):
            cy = ly + 2.4
            if kind == "route":
                c.setStrokeColor(self.p["accent"]); c.setLineWidth(1.6); c.setDash(4, 2.6)
                c.line(xx, cy, xx + 12, cy); c.setDash()
            elif kind == "area":
                c.setFillColor(tint(self.p["gold"], mapgen.AREA_TINT)); c.setStrokeColor(tint(self.p["accent"], 0.35))
                c.setLineWidth(0.7); c.setDash(1.6, 1.4); c.circle(xx + 6, cy, 5.5, stroke=1, fill=1)
                c.setDash(); c.setFillColor(self.p["accent"]); c.circle(xx + 6, cy, 3.4, stroke=0, fill=1)
            elif kind == "cafe":
                mapgen._cafe_symbol(c, xx + 6, cy, self.p["accent2"], tint(self.p["paper"], 0.2))
            else:
                c.setFillColor(tint(self.p["gold"], 0.70)); c.rect(xx + 1, cy - 3.5, 10, 7, stroke=0, fill=1)
            self.left(xx + 16, ly, label, "Body", 6.6, self.p["accent2"])
            xx += ww
        y = ly - 12
        y = self.para(M, y, model.notes["representation_note"] or
                      "Drawn from OpenStreetMap data and simplified. North is up.",
                      "Body-Italic", 6.6, PW - 2 * M, 8.6, self.p["accent2"], align="center") - 13
        if self.s.get("draft_label"):
            self.centered(y, self.s["draft_label"], "Body", 6.6, self.p["accent"], tracking=1.2)
            y -= 14
        if cafes:
            names = [c["name"] for c in cafes]
            joined = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " or " + names[-1]
            after = model.cafes[0]["after_stop"] if model.cafes else ""
            y = self.para(M, y, f"Café break after stop {after}: {joined}. From OpenStreetMap; check "
                                f"opening hours before you go.", "Body", 7.4, PW - 2 * M, 10.2,
                          self.p["accent2"], align="center") - 13
        if carry is not None:
            y = self.para(M, y, f"The walk continues from stop {carry}.", "Body", 8.2, PW - 2 * M, 11.6,
                          self.p["accent"], align="center") - 15
        if first:
            y = self.para(M, y, model.notes["route_note"], "Body", 8.2, PW - 2 * M, 11.6,
                          self.p["accent"], align="center") - 15
        if last:
            y = self.para(M + 6, y, model.notes["mechanic_note"], self.display_i, 12,
                          PW - 2 * M - 12, 15, self.p["ink"], align="center") - 13
        if measure:
            return y0 - y
        if y < M + 18:
            raise mapgen.MapError("map page captions overflow the page")
        self.diamond_rule(y, half=52)
        self.page_break()

    def map_only(self):
        """Render just the trail-map page (standalone map tests)."""
        self.trail_map()
        self.c.save()
        return self.page_no

    def acts(self):
        a = self.s["acts"]
        self.background()
        self.frame()
        y = self.page_head(a["kicker"], a["title_lines"], title_size=21)
        x, W = M, PW - 2 * M
        y = self.para(x, y, a["lede"], "Body", 9.3, W, 13.2, align="center") - 26
        c = self.c
        top = y
        for i, act in enumerate(a["items"]):
            cy = y + 4
            c.setStrokeColor(self.p["accent"])
            c.setLineWidth(0.9)
            c.circle(x + 15, cy, 13.5, stroke=1, fill=0)
            c.setStrokeColor(tint(self.p["gold"], 0.2))
            c.setLineWidth(0.5)
            c.circle(x + 15, cy, 10.5, stroke=1, fill=0)
            self.left(x + 15 - self.text_width(act["numeral"], "Body", 7.4) / 2,
                      cy - 2.6, act["numeral"], "Body", 7.4, self.p["accent2"])
            self.left(x + 40, y, act["name"], self.display, 16.5, self.p["accent"])
            y -= 21
            y = self.para(x + 40, y, act["text"], "Body", 9.1, W - 42, 13) - 15
            if i < len(a["items"]) - 1:
                c.setStrokeColor(tint(self.p["gold"], 0.3))
                c.setLineWidth(0.5)
                c.setDash(1, 3)
                c.line(x + 15, y + 8, x + 15, y - 6)
                c.setDash()
                c.setStrokeColor(tint(self.p["gold"], 0.45))
                c.setLineWidth(0.5)
                c.line(x + 40, y + 2, PW - M, y + 2)
                y -= 20
        y -= 14
        for i, dx in enumerate((-62, 0, 62)):
            cx = PW / 2 + dx
            c.setStrokeColor(tint(self.p["gold"], 0.1))
            c.setLineWidth(0.8)
            c.circle(cx, y, 9, stroke=1, fill=0)
            c.setFillColor(self.p["accent"] if i == 1 else self.p["gold"])
            c.saveState()
            c.translate(cx, y)
            c.rotate(45)
            c.rect(-2, -2, 4, 4, stroke=0, fill=1)
            c.restoreState()
            if dx > -62:
                c.setStrokeColor(tint(self.p["gold"], 0.35))
                c.setLineWidth(0.6)
                c.line(cx - 53, y, cx - 9, y)
        y -= 34
        c.setStrokeColor(tint(self.p["gold"], 0.4))
        c.setLineWidth(0.5)
        c.line(M + 20, y + 14, PW - M - 20, y + 14)
        self.para(M + 10, y, a["closer"], self.display_i, 11.6, W - 20, 14.6,
                  self.p["accent2"], align="center")
        self.page_break()

    def maker(self):
        mk = self.s["maker"]
        self.background()
        self.frame()
        y = self.page_head(mk["kicker"], mk["title_lines"], title_size=21)
        x, W = M, PW - 2 * M
        y = self.para(x, y, mk["standfirst"], self.display_i, 12.4, W, 16,
                      self.p["accent2"], align="center") - 17
        for p in mk["paras"]:
            y = self.para(x, y, p, "Body", 9.3, W, 13.4, align="justify") - 14
        y -= 6
        self.diamond_rule(y + 4, half=56)
        y -= 20
        y = self.section_label(x, y, mk["facts_title"])
        c = self.c
        for label, val in mk["facts"]:
            self.left(x + 4, y, label, "Body", 8.4, self.p["accent"])
            lw = self.text_width(label, "Body", 8.4)
            c.setStrokeColor(tint(self.p["gold"], 0.45))
            c.setLineWidth(0.5)
            c.setDash(1, 2)
            c.line(x + 8 + lw, y + 2, PW - M - 4 - self.text_width(val, "Body", 8.4) - 4, y + 2)
            c.setDash()
            c.setFont("Body", 8.4)
            c.setFillColor(self.p["ink"])
            c.drawRightString(PW - M - 4, y, val)
            y -= 15
        y -= 8
        h = self.para_height(mk["pullquote"], self.display_i, 12.2, W - 46, 15.4)
        c.setFillColor(tint(self.p["accent2"], 0.9))
        c.rect(x + 10, y - h + 6, W - 20, h + 10, stroke=0, fill=1)
        c.setStrokeColor(self.p["accent"])
        c.setLineWidth(1.6)
        c.line(x + 10, y - h + 6, x + 10, y + 16)
        self.para(x + 24, y, mk["pullquote"], self.display_i, 12.2, W - 46, 15.4,
                  self.p["accent2"], align="center")
        self.page_break()

    def riddle(self, i, r, total):
        self.background()
        self.frame()
        y = PH - M - 26
        self.kicker(y, f"Stop {i} of {total}")
        y -= 14
        c = self.c
        c.setFillColor(self.p["gold"])
        c.saveState()
        c.translate(PW / 2, y)
        c.rotate(45)
        c.rect(-1.7, -1.7, 3.4, 3.4, stroke=0, fill=1)
        c.restoreState()
        y -= 26
        self.centered(y, f"{i}. {r['name']}", self.display, 22, self.p["accent"])
        y -= 12
        self.diamond_rule(y, half=66)
        y -= 40
        for stanza in r["stanzas"]:
            for ln in stanza:
                self.centered(y, ln, self.display_i, 12.4, self.p["ink"])
                y -= 17.4
            y -= 12
            c.setFillColor(tint(self.p["gold"], 0.25))
            c.saveState()
            c.translate(PW / 2, y + 6)
            c.rotate(45)
            c.rect(-1.3, -1.3, 2.6, 2.6, stroke=0, fill=1)
            c.restoreState()
            y -= 14
        # non-spoiling ornament
        oy = max(y - 40, M + 128)
        self.riddle_ornament(PW / 2, oy, r.get("ornament", "arch"))
        # found it
        by = M + 92
        c.setStrokeColor(self.p["accent"])
        c.setLineWidth(0.9)
        bw = self.text_width("FOUND IT?", "Body", 8) + 2.2 * 8 + 26
        bx = (PW - bw) / 2
        c.rect(bx, by - 3, 9.5, 9.5, stroke=1, fill=0)
        self.left(bx + 18, by, "FOUND IT?", "Body", 8, self.p["accent2"], tracking=2.2)
        # hint well
        hy = M + 62
        htxt = r["hint"]
        hh = self.para_height(htxt, "Body", 8.4, PW - 2 * M - 40, 11.6)
        c.setFillColor(tint(self.p["accent2"], 0.92))
        c.setStrokeColor(tint(self.p["accent2"], 0.5))
        c.setLineWidth(0.6)
        c.setDash(2, 2)
        c.rect(M + 4, hy - hh + 4, PW - 2 * M - 8, hh + 20, stroke=1, fill=1)
        c.setDash()
        c.setFillColor(self.p["accent2"])
        c.rect(M + 4, hy - hh + 4, 2.6, hh + 20, stroke=0, fill=1)
        self.left(M + 16, hy + 10, "NEED A HINT?", "Body", 6.6, self.p["accent2"], tracking=1.2)
        self.para(M + 16, hy - 1, htxt, "Body", 8.4, PW - 2 * M - 40, 11.6, self.p["ink"])
        self.page_break()

    def riddle_ornament(self, cx, cy, kind):
        c = self.c
        c.saveState()
        g = tint(self.p["gold"], 0.05)
        c.setStrokeColor(g)
        c.setFillColor(g)
        if kind == "water":
            c.setLineWidth(1.2)
            for k in range(3):
                p = c.beginPath()
                yy = cy + 10 - k * 10
                p.moveTo(cx - 56, yy)
                for j in range(4):
                    p.curveTo(cx - 56 + j * 28 + 7, yy + 6, cx - 56 + j * 28 + 21, yy - 6,
                              cx - 56 + (j + 1) * 28, yy)
                c.drawPath(p, stroke=1, fill=0)
        elif kind == "column":
            c.setLineWidth(1.1)
            for dx in (-38, -13, 13, 38):
                c.line(cx + dx - 4, cy - 16, cx + dx - 4, cy + 12)
                c.line(cx + dx + 4, cy - 16, cx + dx + 4, cy + 12)
                c.rect(cx + dx - 7, cy + 12, 14, 4, stroke=1, fill=0)
            c.setLineWidth(1.4)
            c.line(cx - 50, cy + 20, cx + 50, cy + 20)
            c.line(cx - 50, cy - 19, cx + 50, cy - 19)
        elif kind == "circle":
            c.setLineWidth(1.1)
            c.circle(cx, cy, 24, stroke=1, fill=0)
            c.circle(cx, cy, 17, stroke=1, fill=0)
            for a in (0, 120, 240):
                import math
                rad = math.radians(a)
                c.setLineWidth(2.4)
                c.setStrokeColor(self.p["paper"])
                c.line(cx + 15 * math.cos(rad), cy + 15 * math.sin(rad),
                       cx + 26 * math.cos(rad), cy + 26 * math.sin(rad))
                c.setStrokeColor(g)
                c.setLineWidth(1.1)
        elif kind == "obelisk":
            c.setLineWidth(1.1)
            p = c.beginPath()
            p.moveTo(cx - 7, cy - 18)
            p.lineTo(cx - 4, cy + 20)
            p.lineTo(cx, cy + 26)
            p.lineTo(cx + 4, cy + 20)
            p.lineTo(cx + 7, cy - 18)
            p.close()
            c.drawPath(p, stroke=1, fill=0)
            c.rect(cx - 13, cy - 26, 26, 8, stroke=1, fill=0)
            c.setLineWidth(0.8)
            c.line(cx - 46, cy - 26, cx - 17, cy - 26)
            c.line(cx + 17, cy - 26, cx + 46, cy - 26)
        elif kind == "star":
            import math
            c.setLineWidth(1.0)
            for k in range(12):
                a = math.radians(k * 30)
                rr = 26 if k % 3 == 0 else 17
                c.line(cx, cy, cx + rr * math.cos(a), cy + rr * math.sin(a))
            c.circle(cx, cy, 5, stroke=1, fill=0)
        elif kind == "crescent":
            c.setLineWidth(1.2)
            p = c.beginPath()
            p.moveTo(cx - 52, cy - 14)
            p.curveTo(cx - 30, cy + 16, cx + 30, cy + 16, cx + 52, cy - 14)
            c.drawPath(p, stroke=1, fill=0)
            c.setLineWidth(0.8)
            for i in range(11):
                x = cx - 48 + i * 9.6
                yt = cy - 14 + (1 - ((x - cx) / 52.0) ** 2) * 26
                c.line(x, cy - 14, x, yt)
        elif kind == "keystone":
            c.setLineWidth(1.1)
            p = c.beginPath()
            p.moveTo(cx - 12, cy - 16)
            p.lineTo(cx - 8, cy + 16)
            p.lineTo(cx + 8, cy + 16)
            p.lineTo(cx + 12, cy - 16)
            p.close()
            c.drawPath(p, stroke=1, fill=0)
            c.setLineWidth(1.3)
            c.line(cx - 52, cy + 16, cx - 12, cy + 16)
            c.line(cx + 12, cy + 16, cx + 52, cy + 16)
            for dx in (-32, 32):
                c.rect(cx + dx - 11, cy - 4, 22, 20, stroke=1, fill=0)
        elif kind == "square":
            c.setLineWidth(1.1)
            c.rect(cx - 24, cy - 18, 48, 36, stroke=1, fill=0)
            c.setLineWidth(0.8)
            c.rect(cx - 14, cy - 10, 28, 20, stroke=1, fill=0)
            c.setLineWidth(1.3)
            c.line(cx - 52, cy, cx - 28, cy)
            c.line(cx + 28, cy, cx + 52, cy)
        elif kind == "grid":
            c.setLineWidth(0.9)
            for i in range(4):
                c.rect(cx - 54 + i * 28, cy - 14, 22, 28, stroke=1, fill=0)
                c.line(cx - 54 + i * 28, cy + 4, cx - 54 + i * 28 + 22, cy + 4)
        else:  # arch
            c.setLineWidth(1.1)
            for dx in (-30, 0, 30):
                c.line(cx + dx - 9, cy - 16, cx + dx - 9, cy + 4)
                c.line(cx + dx + 9, cy - 16, cx + dx + 9, cy + 4)
                p = c.beginPath()
                p.moveTo(cx + dx - 9, cy + 4)
                p.curveTo(cx + dx - 9, cy + 16, cx + dx + 9, cy + 16, cx + dx + 9, cy + 4)
                c.drawPath(p, stroke=1, fill=0)
            c.setLineWidth(1.4)
            c.line(cx - 46, cy + 19, cx + 46, cy + 19)
            c.line(cx - 46, cy - 17, cx + 46, cy - 17)
        c.restoreState()

    def spoiler(self):
        sp = self.s["spoiler"]
        self.background()
        self.frame(heavy=True)
        y = PH - 1.9 * inch
        self.kicker(y, "Spoilers ahead", self.p["accent"], size=7.6)
        y -= 22
        self.diamond_rule(y, half=52)
        y -= 44
        for ln in sp["title_lines"]:
            self.centered(y, ln, self.display, 25, self.p["accent"])
            y -= 30
        y -= 4
        c = self.c
        c.setStrokeColor(self.p["accent"])
        c.setLineWidth(1.5)
        c.line(M + 18, y, PW - M - 18, y)
        c.setLineWidth(0.6)
        c.line(M + 18, y - 3.4, PW - M - 18, y - 3.4)
        y -= 30
        y = self.para(M, y, sp["lede"], "Body", 9.6, PW - 2 * M, 13.4, align="center") - 30
        self.motif(PW / 2, y - 52, 48, "arch")
        y -= 132
        self.left(M + 22, y, sp["check_title"], "Body", 8, self.p["accent2"], tracking=0.8)
        y -= 20
        for item in sp["checks"]:
            c.setStrokeColor(self.p["accent2"])
            c.setLineWidth(0.8)
            c.rect(M + 22, y - 2, 9, 9, stroke=1, fill=0)
            self.left(M + 40, y, item, self.display, 12.4, self.p["ink"])
            y -= 19
        y -= 10
        self.diamond_rule(y, half=52)
        self.page_break()

    def answer(self, i, a, total):
        self.background()
        self.frame()
        c = self.c
        # header band
        ty = PH - M - 14
        c.setFillColor(self.p["accent"])
        c.circle(M + 10, ty + 2, 10.5, stroke=0, fill=1)
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont("Body", 8.4)
        c.drawCentredString(M + 10, ty - 1, str(i))
        self.left(M + 27, ty - 2, f"Stop {i} on the route", "Body", 6.8,
                  self.p["accent2"], tracking=1.4)
        badge = f"ANSWER {i}"
        bw = self.text_width(badge, "Body", 6.8) + 2 * 1.4 + 20
        c.setFillColor(self.p["gold"])
        c.roundRect(PW - M - bw, ty - 6, bw, 16, 3, stroke=0, fill=1)
        self.left(PW - M - bw + 10, ty - 1.5, badge, "Body", 6.8, HexColor("#FFFFFF"), tracking=1.4)
        y = ty - 18
        c.setStrokeColor(tint(self.p["gold"], 0.35))
        c.setLineWidth(0.6)
        c.line(M, y, PW - M, y)
        y -= 24
        self.centered(y, f"Answer {i} — {a['name']}", self.display, 19.5, self.p["accent"])
        y -= 22
        for ln in a["subtitle_lines"]:
            self.centered(y, ln, self.display_i, 11.4, self.p["accent2"])
            y -= 14.6
        y -= 2
        self.diamond_rule(y, half=44)
        y -= 14
        # ---- measure everything below the title, then fit -------------
        img = os.path.join(IMG_DIR, a["image"])
        ir = ImageReader(img)
        w0, h0 = ir.getSize()
        nt = a["notice"]
        W = PW - 2 * M
        avail = y - (M + 16)

        def measure(sc, maxh):
            iw = 2.85 * inch
            ih = iw * h0 / w0
            if ih > maxh:
                ih = maxh
                iw = ih * w0 / h0
            t = ih + 11
            t += self.para_height(a["credit"], "Body", 5.9, W - 28, 8.2) + 12
            for p in a["paras"]:
                t += self.para_height(p, "Body", 8.7 * sc, W, 12.3 * sc) + 11 * sc
            t += 8
            for label, txt in a["blocks"]:
                t += 11.4 * sc + self.para_height(txt, "Body", 8.3 * sc, W - 14,
                                                  11.4 * sc) + 12 * sc
            t += 22
            t += self.para_height(nt[1], "Body", 8.2 * sc, W - 40, 11.2 * sc) + 24
            return t, iw, ih

        sc, maxh = 1.0, 1.62 * inch
        for cand_h in (2.70, 2.55, 2.40, 2.25, 2.10, 1.95, 1.80, 1.66, 1.52, 1.38, 1.24, 1.12):
            for cand_s in (1.0, 0.97, 0.94, 0.91, 0.88, 0.85, 0.82, 0.79):
                t, _, _ = measure(cand_s, cand_h * inch)
                if t <= avail:
                    sc, maxh = cand_s, cand_h * inch
                    break
            else:
                continue
            break
        else:
            sc, maxh = 0.79, 1.12 * inch
        t, iw, ih = measure(sc, maxh)
        slack = avail - t
        if slack > 24:
            y -= min(slack * 0.42, 46)

        # ---- image ----------------------------------------------------
        ix = (PW - iw) / 2
        c.drawImage(ir, ix, y - ih, iw, ih, preserveAspectRatio=True, mask='auto')
        c.setStrokeColor(tint(self.p["accent2"], 0.55))
        c.setLineWidth(0.6)
        c.rect(ix, y - ih, iw, ih, stroke=1, fill=0)
        y = y - ih - 11
        y = self.para(M + 14, y, a["credit"], "Body", 5.9, W - 28, 8.2,
                      self.p["accent2"], align="center") - 12
        for p in a["paras"]:
            y = self.para(M, y, p, "Body", 8.7 * sc, W, 12.3 * sc, align="justify") - 11 * sc
        y -= 2
        c.setStrokeColor(tint(self.p["gold"], 0.45))
        c.setLineWidth(0.5)
        c.line(M, y + 8, PW - M, y + 8)
        y -= 6
        for label, txt in a["blocks"]:
            c.setFillColor(self.p["gold"])
            c.saveState()
            c.translate(M + 3, y + 2.6)
            c.rotate(45)
            c.rect(-1.6, -1.6, 3.2, 3.2, stroke=0, fill=1)
            c.restoreState()
            self.left(M + 11, y, label.upper(), "Body", 6.7, self.p["accent2"], tracking=1.3)
            y -= 11.4 * sc
            y = self.para(M + 11, y, txt, "Body", 8.3 * sc, W - 14, 11.4 * sc) - 12 * sc
        # notice well
        y -= 22
        nh = self.para_height(nt[1], "Body", 8.2 * sc, W - 40, 11.2 * sc)
        c.setFillColor(tint(self.p["gold"], 0.86))
        c.setStrokeColor(tint(self.p["gold"], 0.35))
        c.setLineWidth(0.6)
        c.setDash(2, 2)
        c.rect(M + 4, y - nh + 4, PW - 2 * M - 8, nh + 20, stroke=1, fill=1)
        c.setDash()
        c.setFillColor(self.p["gold"])
        c.rect(M + 4, y - nh + 4, 2.6, nh + 20, stroke=0, fill=1)
        self.left(M + 16, y + 10, nt[0].upper(), "Body", 6.6, self.p["accent2"], tracking=1.2)
        self.para(M + 16, y - 1, nt[1], "Body", 8.2 * sc, W - 40, 11.2 * sc, self.p["ink"])
        if y - nh + 4 < M + 6:
            print(f"  !! answer {i} overflow, bottom =", round(y - nh + 4, 1))
        self.page_break()

    def closing(self):
        cl = self.s["closing"]
        self.background()
        self.frame()
        y = self.page_head(cl["kicker"], cl["title_lines"], title_size=24)
        x, W = M, PW - 2 * M
        for p in cl["paras"]:
            y = self.para(x, y, p, "Body", 9.4, W, 13.6, align="justify") - 15
        y -= 6
        self.diamond_rule(y + 4, half=56)
        y -= 26
        self.centered(y, cl["notes_title"], self.display, 16, self.p["accent"])
        y -= 24
        c = self.c
        for lab in cl["note_fields"]:
            self.left(x + 6, y, lab, "Body", 8.8, self.p["ink"])
            lw = self.text_width(lab, "Body", 8.8)
            c.setStrokeColor(tint(self.p["gold"], 0.2))
            c.setLineWidth(0.6)
            c.line(x + 12 + lw, y - 2, PW - M - 6, y - 2)
            y -= 23
        y -= 6
        h = self.para_height(cl["pullquote"], self.display_i, 12.6, W - 40, 16)
        c.setFillColor(tint(self.p["accent2"], 0.9))
        c.rect(x + 8, y - h + 6, W - 16, h + 10, stroke=0, fill=1)
        self.para(x + 22, y, cl["pullquote"], self.display_i, 12.6, W - 44, 16,
                  self.p["accent2"], align="center")
        self.page_break()

    def credits(self):
        cr = self.s["credits"]
        self.background()
        self.frame()
        y = self.page_head("Sources and credits", cr["title_lines"], title_size=20)
        x, W = M, PW - 2 * M
        y = self.para(x, y, cr["intro"], "Body", 8.4, W, 11.8, align="justify") - 16
        y = self.section_label(x, y, "Photographs")
        for line in cr["images"]:
            y = self.para(x + 6, y, line, "Body", 6.9, W - 8, 9.4,
                          self.p["ink"], first_indent=0) - 7
        y -= 8
        y = self.section_label(x, y, "Written sources")
        for line in cr["sources"]:
            y = self.para(x + 6, y, line, "Body", 6.9, W - 8, 9.4, self.p["ink"]) - 7
        y -= 10
        self.diamond_rule(y + 4, half=52)
        y -= 20
        self.para(x + 10, y, cr["colophon"], self.display_i, 10.4, W - 20, 13.4,
                  self.p["accent2"], align="center")
        self.page_break()

    def blank_with_ornament(self, label):
        self.background()
        self.frame()
        self.motif(PW / 2, PH / 2 + 20, 52, self.s.get("cover_motif", "arch"))
        self.diamond_rule(PH / 2 - 78, half=52)
        self.centered(PH / 2 - 108, label, self.display_i, 12, self.p["accent2"])
        self.page_break()

    # ---- orchestration ---------------------------------------------

    def build(self):
        s = self.s
        n = len(s["stops"])
        if s.get("map", {}).get("version") == 2:
            import mapgen
            if len(s["map"]["stops"]) != n:
                raise mapgen.MapError("map stops and book stops differ in number")
            waived = [i for i, st in enumerate(s["map"]["stops"], 1) if st.get("order_waiver")]
            if waived:
                raise mapgen.MapError(f"order waivers are for map-only tests; a book cannot waive the "
                                      f"ticketed-stops-last rule (stops {waived})")
            errs = mapgen.spoiler_scan(mapgen.pre_divider_texts(s), s["map"]["stops"])
            if errs:
                raise mapgen.MapError("pre-divider spoiler check failed:\n  " + "\n  ".join(errs))
        self.cover()
        self.how_to_play()
        self.trail_map()
        self.acts()
        self.maker()
        for i, r in enumerate(s["stops"], 1):
            self.riddle(i, r["riddle"], n)
        self.spoiler()
        for i, r in enumerate(s["stops"], 1):
            self.answer(i, r["answer"], n)
        self.closing()
        self.credits()
        while self.page_no % 4 != 0:
            self.blank_with_ornament(s.get("blank_label", "Notes"))
        self.c.save()
        return self.page_no
