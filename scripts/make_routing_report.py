#!/usr/bin/env python3
"""Build the routing PDF (every routed connection, layer usage, checks, open items)."""
import json, math, os, sys
from collections import defaultdict, Counter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                Image, PageBreak)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sexpr import parse, find, first, val  # noqa: E402

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
BOARD = os.path.join(ROOT, "sv16_board_routed_draft.kicad_pcb")
ROUTES = os.path.join(ROOT, "routing", "sv16_routes.json")
VERIF = os.path.join(ROOT, "routing", "verification_report.json")
RULES = os.path.join(ROOT, "routing", "sv16_design_rules.json")
PDF = os.path.join(ROOT, "SV16_routing_report.pdf")
FIG = os.path.join(ROOT, "routing")

t = parse(open(BOARD, encoding="utf-8").read())
routes = json.load(open(ROUTES))
verif = json.load(open(VERIF))
rules = json.load(open(RULES))

# ---------- geometry from the routed board file
xs, ys = [], []
for gl in find(t, "gr_line"):
    if val(first(gl, "layer")[1]) == "Edge.Cuts":
        for k in ("start", "end"):
            q = first(gl, k); xs.append(float(q[1][1])); ys.append(float(q[2][1]))
BX0, BY0, BX1, BY1 = min(xs), min(ys), max(xs), max(ys)

segs = []
for s in find(t, "segment"):
    a = first(s, "start"); b = first(s, "end")
    segs.append(dict(a=(float(a[1][1]), float(a[2][1])), b=(float(b[1][1]), float(b[2][1])),
                     w=float(first(s, "width")[1][1]), layer=val(first(s, "layer")[1]),
                     net=val(first(s, "net")[1])))
vias = []
for v in find(t, "via"):
    at = first(v, "at")
    vias.append(dict(x=float(at[1][1]), y=float(at[2][1]), net=val(first(v, "net")[1])))

pads = []
for f in find(t, "footprint"):
    at = first(f, "at"); fx, fy = float(at[1][1]), float(at[2][1])
    fr = float(at[3][1]) if len(at) > 3 else 0.0
    ref = [val(x[2]) for x in find(f, "property") if val(x[1]) == "Reference"][0]
    r = math.radians(fr); c, s_ = math.cos(r), math.sin(r)
    for p in find(f, "pad"):
        pat = first(p, "at"); px, py = float(pat[1][1]), float(pat[2][1])
        sz = first(p, "size"); w, h = float(sz[1][1]), float(sz[2][1])
        ax = fx + (px * c + py * s_); ay = fy + (-px * s_ + py * c)
        n = first(p, "net"); net = val(n[1]) if n else ""
        pads.append(dict(id=f"{ref}.{val(p[1])}", net=net, x=ax, y=ay, w=w, h=h,
                         th=val(p[2]) in ("thru_hole", "np_thru_hole"), ref=ref))

seg_len = defaultdict(float)     # per layer
net_len = defaultdict(float)
for s in segs:
    L = math.hypot(s["b"][0] - s["a"][0], s["b"][1] - s["a"][1])
    seg_len[s["layer"]] += L
    net_len[s["net"]] += L

# ---------- figures
def draw(ax, layer_filter, title):
    ax.set_aspect("equal")
    ax.add_patch(plt.Rectangle((BX0, BY0), BX1 - BX0, BY1 - BY0, fill=False, ec="black", lw=1.2))
    for p in pads:
        if p["th"]:
            col = "#c9a227"
        else:
            col = "#9aa5b1"
        ax.add_patch(plt.Rectangle((p["x"] - p["w"] / 2, p["y"] - p["h"] / 2), p["w"], p["h"],
                                   color=col, lw=0, alpha=0.9))
    for s in segs:
        if s["layer"] in layer_filter:
            c = "#d62828" if s["layer"] == "F.Cu" else "#1d4ed8"
            ax.plot([s["a"][0], s["b"][0]], [s["a"][1], s["b"][1]], color=c,
                    lw=max(0.6, s["w"] * 2.2), solid_capstyle="round", alpha=0.85)
    for v in vias:
        ax.add_patch(plt.Circle((v["x"], v["y"]), 0.25, color="#111111", zorder=5))
        ax.add_patch(plt.Circle((v["x"], v["y"]), 0.125, color="#ffffff", zorder=6))
    ax.set_xlim(BX0 - 3, BX1 + 3); ax.set_ylim(BY1 + 3, BY0 - 3)  # y down like KiCad
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("x (mm)"); ax.set_ylabel("y (mm)")

figs = {}
for name, lays, title in [
    ("fig_F_Cu.png", ["F.Cu"], "F.Cu (top) - routed copper; red = track, grey = SMD pad, gold = through-hole"),
    ("fig_B_Cu.png", ["B.Cu"], "B.Cu (bottom) - routed copper; blue = track"),
]:
    fig, ax = plt.subplots(figsize=(10, 10.4), dpi=140)
    draw(ax, lays, title)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, name)); plt.close(fig)
    figs[name] = os.path.join(FIG, name)

fig, ax = plt.subplots(figsize=(10, 10.4), dpi=140)
draw(ax, ["F.Cu", "B.Cu"], "Both signal layers (red F.Cu, blue B.Cu), black dots = vias (In1 GND / In2 3V3 reached through them)")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_both.png")); plt.close(fig)
figs["fig_both.png"] = os.path.join(FIG, "fig_both.png")

# ---------- text content
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontSize=16, spaceAfter=6)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, spaceBefore=8, spaceAfter=4)
B = ParagraphStyle("B", parent=ss["BodyText"], fontSize=8.8, leading=11.2)
SM = ParagraphStyle("SM", parent=ss["BodyText"], fontSize=7.2, leading=8.6)
WARN = ParagraphStyle("W", parent=B, textColor=colors.HexColor("#9b1c1c"))

summ = routes["summary"]
routes_by_net = routes["routes"]
failures = summ["failures"]
open_pads = defaultdict(list)
for n, pid in failures:
    open_pads[n].append(pid)

story = []
story.append(Paragraph("SV16 Rev A FPGA board - routing report (DRAFT, not a fabrication release)", H1))
story.append(Paragraph(
    "Source placement: <i>sv16_board_placed_native.kicad_pcb</i> (placement only, 0 copper). "
    "Routed output: <i>sv16_board_routed_draft.kicad_pcb</i>. Stackup: F.Cu signals, In1.Cu GND plane, "
    "In2.Cu 3V3 plane, B.Cu signals (4 layers, as specified in the handoff).", B))
story.append(Spacer(1, 4))
story.append(Paragraph(
    "<b>Status: routing is NOT complete.</b> %d of %d nets are fully connected; %d pad connections are open "
    "(see section 4). The board must not be sent for fabrication. KiCad DRC, the schematic cross-check and "
    "Gerber/drill export were not possible in this environment (no KiCad installation, no schematic in the "
    "repository)." % (summ["nets_routed"], summ["nets_total"], len(failures)), WARN))

story.append(Paragraph("1. Starting state vs. this routing pass", H2))
vr = verif["summary"]
rows = [["Item", "Handoff says", "Measured in repo file", "Routed draft"],
        ["Footprints", "141", "141", "141"],
        ["Pads", "591", "602", "602"],
        ["Signal nets", "112", "119 named nets with >= 2 pads", "119"],
        ["Tracks (segments)", "0", "0", str(vr["tracks"])],
        ["Vias", "0", "0", str(vr["vias"])],
        ["Copper zones (planes)", "0", "0", "2 defined (GND In1.Cu, 3V3 In2.Cu), unfilled in file"],
        ["Unconnected items", "353", "353 (KiCad, per handoff)", str(vr["unconnected_items"])]]
t1 = Table([[Paragraph(c, SM) for c in r] for r in rows], colWidths=[40 * mm, 30 * mm, 60 * mm, 80 * mm])
t1.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb"))]))
story.append(t1)
story.append(Paragraph(
    "The handoff counts (591 pads, 112 nets) do not match the file (602 pads, 119 named nets). "
    "The file was used as the authority; the difference was not explained in the repository.", SM))

story.append(Paragraph("2. Checks run on the routed file (independent geometry check, shapely)", H2))
rows = [["Check", "Result", "Notes"],
        ["Shorts (different nets touching)", str(vr["shorts"]), ""],
        ["Clearance < 0.15 mm (different nets, same layer)", str(vr["clearance_violations"]), "router masks use 0.16 mm"],
        ["Hole-to-hole < 0.25 mm", str(vr["hole_to_hole"]), ""],
        ["Board-edge violations (< 0.30 mm)", str(vr["board_edge_violations"]), ""],
        ["Dangling track ends", str(vr["dangling_tracks"]), ""],
        ["Dangling vias", str(vr["dangling_vias"]), ""],
        ["Nets fully connected", "%d / %d" % (vr["nets_fully_connected"], vr["nets_with_pads"]),
         "GND / 3V3 counted connected when each SMD pad has a via into the plane"],
        ["Unconnected pad items", str(vr["unconnected_items"]), "section 4"],
        ["Plane islands (GND In1 / 3V3 In2)", "%d / %d" % (vr["plane_islands"]["GND_islands"], vr["plane_islands"]["3V3_islands"]),
         "islands of the recomputed fill; see section 5"],
        ["KiCad DRC / Gerbers / BOM / position file", "not run", "requires KiCad, which is not installed here"]]
t2 = Table([[Paragraph(c, SM) for c in r] for r in rows], colWidths=[85 * mm, 35 * mm, 110 * mm])
t2.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb"))]))
story.append(t2)

story.append(Paragraph("3. Layer usage", H2))
nv = Counter(v["net"] for v in vias)
rows = [["Layer", "Role", "Routed length (mm)", "Via use"],
        ["F.Cu", "signals, FPGA fanout", "%.1f" % seg_len["F.Cu"], "all %d vias pass through every layer" % len(vias)],
        ["In1.Cu", "GND plane (zone, unfilled in file)", "plane", "reached by GND vias / through-hole pads"],
        ["In2.Cu", "3V3 plane (zone, unfilled in file)", "plane", "reached by 3V3 vias / through-hole pads"],
        ["B.Cu", "signals", "%.1f" % seg_len["B.Cu"], ""]]
t3 = Table([[Paragraph(c, SM) for c in r] for r in rows], colWidths=[25 * mm, 70 * mm, 40 * mm, 95 * mm])
t3.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb"))]))
story.append(t3)
story.append(Paragraph(
    "Track widths: signals 0.15 mm, power nets (VM_IN, VM_IN_RAW, J9_VIN, U5_SW, U6_SW, USB_VBUS, 5V_USB, 1V1, 2V5) "
    "0.30 mm. Vias 0.50 mm / 0.25 mm drill. Clearance 0.15 mm. Copper-to-edge 0.30 mm.", SM))

story.append(PageBreak())
story.append(Paragraph("Board figures (coordinates in mm, board origin at the top-left, as in KiCad)", H2))
for name in ["fig_F_Cu.png", "fig_B_Cu.png", "fig_both.png"]:
    story.append(Image(figs[name], width=170 * mm, height=177 * mm))
    story.append(Spacer(1, 4))
story.append(PageBreak())

story.append(Paragraph("4. Open items (pad connections not routed)", H2))
if failures:
    rows = [["Net", "Pad(s) left unrouted", "Note"]]
    for n in sorted(open_pads):
        notes = ""
        if n in ("1V1", "2V5"):
            notes = "FPGA core/IO supply pin, power-width track could not reach it"
        rows.append([n, ", ".join(open_pads[n]), notes])
    t4 = Table([[Paragraph(c, SM) for c in r] for r in rows], colWidths=[30 * mm, 120 * mm, 80 * mm])
    t4.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fde2e2"))]))
    story.append(t4)
story.append(Paragraph(
    "The router runs three passes and keeps the best one. Raising the search budget from 350k to 1.5M expansions gave "
    "the same 22 failures, so these pins are blocked by copper already placed, not by search limits. The next step "
    "is rip-up-and-reroute of the blocking nets or a manual change to the FPGA escape order.", SM))

story.append(Paragraph("5. Unassigned FPGA pins (not routed - no net in the placement file)", H2))
u1_nonet = sorted([p["num"] for p in []])  # placeholder replaced below
unassigned = sorted([p for p in pads if p["ref"] == "U1" and not p["net"]], key=lambda p: int(p["id"].split(".")[1]))
story.append(Paragraph(
    "%d of the 144 FPGA (U1, LFE5U-12F, LQFP-144) pads have no net in the placement file: %s. They are most likely the "
    "FPGA's VCC, VCCIO and GND pins. The schematic that would confirm this is not in the repository, so no net was "
    "assigned and nothing was routed to them. The FPGA cannot be powered from this board until these pins are "
    "assigned from the schematic." % (len(unassigned), ", ".join(p["id"].split(".")[1] for p in unassigned)), WARN))

story.append(Paragraph("6. BOM / release items noted (not changed)", H2))
for line in [
    "L1 = 10 uH, Sunlord SWPA6045S (feeds U5, AP62300TWU-7 step-down).",
    "L2 = 10 uH, Sunlord SWPA6045S (feeds U6, MP1584EN). The handoff reports a cart record for 33 uH; the value was NOT changed. "
    "The MP1584 datasheet design table and the purchased part's current rating must be checked by a person.",
    "Y1 = 25 MHz active oscillator, Abracon ASE 4-pin 3.2x2.5 mm. Pin 1 / enable / output pin order must be checked against the "
    "purchased part; the footprint pinout was not verified against a datasheet here.",
    "U5/U6 passives, switching-node ringing, and inductor current ratings were not verified (no schematic or datasheet in the repository).",
]:
    story.append(Paragraph("- " + line, B))

story.append(PageBreak())
story.append(Paragraph("7. Every routed connection", H2))
story.append(Paragraph(
    "Each row is one connection the router added. For signal nets the first pad of the net is the anchor; each row joins one "
    "more pad to the copper already connected to it. For GND and 3V3 each SMD pad gets its own via into the plane. "
    "'Layers' is the copper used by that connection; 'Len' is the track length in mm; 'Vias' is the number of vias the "
    "connection uses.", SM))
story.append(Spacer(1, 3))

anchor = {}
pads_by_net = defaultdict(list)
for p in pads:
    if p["net"]:
        pads_by_net[p["net"]].append(p)

rows = [[Paragraph(h, SM) for h in ["Net", "Width", "From (anchor/plane)", "To pad", "Layers", "Len mm", "Vias", "Status"]]]
rows_fmt = []
for net in sorted(routes_by_net, key=lambda n: (n in ("GND", "3V3"), n)):
    rec = routes_by_net[net]
    w = rec["width"]
    conns = rec["connections"]
    if net in ("GND", "3V3"):
        for c in conns:
            L = ",".join(sorted({tr["layer"] for tr in c["tracks"]})) or "pad-via"
            ln = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for tr in c["tracks"] for a, b in zip(tr["points"][:-1], tr["points"][1:]))
            rows_fmt.append([net, "%.2f" % w, rec["plane"] + " plane", c["pad"], L, "%.2f" % ln, str(len(c["vias"])), "routed"])
        for pid in rec["unrouted"]:
            rows_fmt.append([net, "%.2f" % w, rec["plane"] + " plane", pid, "-", "-", "-", "OPEN"])
        continue
    connected = [c["to"] for c in conns]
    allp = [p["id"] for p in pads_by_net[net]]
    open_ids = set(rec["unrouted"])
    anchor_ids = [pid for pid in allp if pid not in connected and pid not in open_ids]
    anc = anchor_ids[0] if anchor_ids else "?"
    for c in conns:
        L = ",".join(sorted({tr["layer"] for tr in c["tracks"]})) or "pad"
        ln = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for tr in c["tracks"] for a, b in zip(tr["points"][:-1], tr["points"][1:]))
        rows_fmt.append([net, "%.2f" % w, anc + " (tree)", c["to"], L, "%.2f" % ln, str(len(c["vias"])), "routed"])
    for pid in open_ids:
        rows_fmt.append([net, "%.2f" % w, anc + " (tree)", pid, "-", "-", "-", "OPEN"])

for r in rows_fmt:
    rows.append([Paragraph(str(x), SM) for x in r])
t5 = Table(rows, colWidths=[24 * mm, 13 * mm, 40 * mm, 30 * mm, 27 * mm, 16 * mm, 12 * mm, 16 * mm], repeatRows=1)
sty = [("GRID", (0, 0), (-1, -1), 0.2, colors.lightgrey),
       ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
       ("VALIGN", (0, 0), (-1, -1), "TOP")]
for k, r in enumerate(rows_fmt, start=1):
    if r[-1] == "OPEN":
        sty.append(("BACKGROUND", (0, k), (-1, k), colors.HexColor("#fde2e2")))
t5.setStyle(TableStyle(sty))
story.append(t5)

story.append(Paragraph("8. Not done / limits of this draft", H2))
for line in [
    "No KiCad installation here: DRC, zone refill and project-open check were not run. Open the file in KiCad 10 and press B (fill all zones), then run DRC.",
    "The two plane zones are defined but not filled in the file; the fill I recomputed for checking is not written to the board.",
    "Thermal reliefs for plane connections are not drawn in my model; KiCad creates them when the zones are filled.",
    "The router uses a 0.10 mm grid with 45-degree steps; track geometry was verified with exact shape clearance, not with KiCad's engine.",
    "Rotated-footprint pads use KiCad's rotation convention (x' = x*cos + y*sin, y' = -x*sin + y*cos), confirmed against KiCad's source discussion; a KiCad check is still required.",
    "No schematic was available: the 112/119 net list is taken from the PCB pad net names, not compared to a schematic.",
    "Courtyard routing rule was not enforced. Tracks may pass over component bodies where pad clearance allows.",
]:
    story.append(Paragraph("- " + line, B))

doc = SimpleDocTemplate(PDF, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm,
                        topMargin=12 * mm, bottomMargin=12 * mm, title="SV16 routing report (draft)")
doc.build(story)
print("wrote", PDF, "connections:", len(rows_fmt))
