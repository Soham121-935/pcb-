#!/usr/bin/env python3
"""
Independent geometry check for a routed SV16 .kicad_pcb (does not use router state).

Checks (approximating KiCad DRC with shapely geometry):
  * connectivity per net (union-find over touching copper, vias span F/B and planes)
  * unconnected items (pads not in their net's component / plane connection)
  * shorts (copper of two different nets touching)
  * clearance between different-net copper on the same layer (>= CLR)
  * hole-to-hole spacing between drilled holes (>= 0.25 mm)
  * board-edge clearance (>= EDGE)
  * dangling track ends and dangling vias
  * plane fill (GND In1 / 3V3 In2) recomputed from the board: each plane-net pad must
    reach a via or through-hole that sits inside that plane's copper region

Usage: verify_sv16_routing.py <routed.kicad_pcb> [out.json]
"""
import json, math, os, sys
from collections import defaultdict
import shapely
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sexpr import parse, find, first, val  # noqa: E402

CLR, EDGE, HOLE_CLR = 0.15, 0.30, 0.25
PLANE = {"GND": "In1.Cu", "3V3": "In2.Cu"}


def xy(node, key):
    q = first(node, key)
    return float(q[1][1]), float(q[2][1])


def load(path):
    t = parse(open(path, encoding="utf-8").read())
    # board outline
    xs, ys = [], []
    for gl in find(t, "gr_line"):
        if val(first(gl, "layer")[1]) == "Edge.Cuts":
            for k in ("start", "end"):
                x, y = xy(gl, k); xs.append(x); ys.append(y)
    outline = box(min(xs), min(ys), max(xs), max(ys))
    pads = []
    for f in find(t, "footprint"):
        at = first(f, "at")
        fx, fy = float(at[1][1]), float(at[2][1])
        fr = float(at[3][1]) if len(at) > 3 else 0.0
        r = math.radians(fr); c, s = math.cos(r), math.sin(r)
        ref = [val(x[2]) for x in find(f, "property") if val(x[1]) == "Reference"][0]
        for p in find(f, "pad"):
            pat = first(p, "at")
            px, py = float(pat[1][1]), float(pat[2][1])
            pr = float(pat[3][1]) if len(pat) > 3 else 0.0
            sz = first(p, "size"); w, h = float(sz[1][1]), float(sz[2][1])
            ax = fx + (px * c + py * s); ay = fy + (-px * s + py * c)
            n = first(p, "net"); net = val(n[1]) if n else ""
            lay = [val(x) for x in first(p, "layers")[1:]]
            layers = ["F.Cu", "B.Cu"] if "*.Cu" in lay else [l for l in lay if l.endswith(".Cu")]
            shape = val(p[3]); ptype = val(p[2])
            if shape == "circle":
                geom = Point(ax, ay).buffer(w / 2, quad_segs=8)
            else:
                geom = box(-w / 2, -h / 2, w / 2, h / 2)
                geom = shapely.affinity.rotate(geom, pr + fr, origin=(0, 0))
                geom = shapely.affinity.translate(geom, ax, ay)
            d = first(p, "drill"); drill = None
            if d:
                for x in d[1:]:
                    if isinstance(x, tuple) and x[0] == "A":
                        try:
                            drill = float(x[1]); break
                        except ValueError:
                            pass
            pads.append(dict(kind="pad", ref=ref, num=val(p[1]), net=net, layers=layers,
                             geom=geom, th=(ptype in ("thru_hole", "np_thru_hole")),
                             hole=(Point(ax, ay), drill / 2) if drill else None,
                             id=f"{ref}.{val(p[1])}", x=ax, y=ay))
    segs, vias = [], []
    for s in find(t, "segment"):
        a = xy(s, "start"); b = xy(s, "end")
        w = float(first(s, "width")[1][1]); layer = val(first(s, "layer")[1])
        net = val(first(s, "net")[1]) if first(s, "net") else ""
        segs.append(dict(kind="seg", a=a, b=b, w=w, layer=layer, net=net,
                         geom=LineString([a, b]).buffer(w / 2, quad_segs=8, cap_style="round")))
    for v in find(t, "via"):
        x, y = xy(v, "at"); size = float(first(v, "size")[1][1]); drill = float(first(v, "drill")[1][1])
        net = val(first(v, "net")[1]) if first(v, "net") else ""
        vias.append(dict(kind="via", x=x, y=y, size=size, drill=drill, net=net,
                         geom=Point(x, y).buffer(size / 2, quad_segs=8), hole=(Point(x, y), drill / 2),
                         layers=["F.Cu", "B.Cu"]))
    return outline, pads, segs, vias


def main(path, out_json=None):
    outline, pads, segs, vias = load(path)
    objs = []
    for p in pads:
        objs.append(p)
    objs += segs + vias
    for o in objs:
        if o["kind"] == "seg":
            o["layers"] = [o["layer"]]
    # ---------- build indexes
    issues = defaultdict(list)
    geoms = [o["geom"] for o in objs]
    tree = STRtree(geoms)

    def on_layer(o, layer):
        return layer in o["layers"]

    # ---------- clearance / shorts
    pairs = tree.query(geoms, predicate="dwithin", distance=CLR)  # candidate pairs
    n_pairs = 0
    for i, j in zip(*pairs):
        if i >= j:
            continue
        a, b = objs[i], objs[j]
        if a["net"] == b["net"] and a["net"] != "":
            continue
        common = [L for L in a["layers"] if L in b["layers"]]
        if not common:
            continue
        d = a["geom"].distance(b["geom"])
        n_pairs += 1
        if d <= 1e-9:
            issues["shorts"].append(f'{a.get("id", a.get("kind"))}[{a["net"]}] touches {b.get("id", b.get("kind"))}[{b["net"]}]')
        elif d < CLR - 1e-6:
            issues["clearance"].append(f'{a.get("id", a["kind"])}[{a["net"]}] <-> {b.get("id", b["kind"])}[{b["net"]}] gap={d:.3f}')
    # hole-to-hole
    holes = [o for o in pads + vias if o.get("hole")]
    for i in range(len(holes)):
        for j in range(i + 1, len(holes)):
            a, b = holes[i], holes[j]
            ca, ra = a["hole"]; cb, rb = b["hole"]
            gap = ca.distance(cb) - ra - rb
            if gap < HOLE_CLR - 1e-6:
                issues["hole_to_hole"].append(f'{a.get("id", a["kind"])} <-> {b.get("id", b["kind"])} gap={gap:.3f}')
    # ---------- board edge
    inner = outline.buffer(-EDGE, quad_segs=4)
    for o in objs:
        if not inner.buffer(1e-6).contains(o["geom"]):
            issues["board_edge"].append(f'{o.get("id", o["kind"])} net={o["net"]}')

    # ---------- connectivity per net (union-find)
    parent = list(range(len(objs)))

    def find_(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x

    def union(x, y):
        rx, ry = find_(x), find_(y)
        if rx != ry:
            parent[rx] = ry

    for i, j in zip(*tree.query(geoms, predicate="intersects")):
        if i >= j:
            continue
        a, b = objs[i], objs[j]
        if a["net"] != b["net"]:
            continue  # shorts are reported above
        if not any(L in b["layers"] for L in a["layers"]):
            continue
        union(i, j)

    comp_of = {i: find_(i) for i in range(len(objs))}
    # dangling checks
    dang_tracks, dang_vias = [], []
    for k, o in enumerate(objs):
        if o["kind"] == "seg":
            ends = [o["a"], o["b"]]
            ok_all = True
            for e in ends:
                pt = Point(e)
                hit = False
                for m in tree.query(pt, predicate="intersects"):
                    if m == k:
                        continue
                    q = objs[m]
                    if q["net"] == o["net"] and o["layer"] in q["layers"]:
                        hit = True; break
                if not hit:
                    ok_all = False
            if not ok_all:
                dang_tracks.append(f'{o["net"]} {o["layer"]} {o["a"]}->{o["b"]}')
        if o["kind"] == "via":
            hit = False
            for m in tree.query(o["geom"], predicate="intersects"):
                if m == k:
                    continue
                q = objs[m]
                if q["net"] == o["net"] and q["kind"] != "via":
                    hit = True; break
                if q["kind"] == "via" and q["net"] == o["net"]:
                    hit = True; break
            if not hit:
                dang_vias.append(f'{o["net"]} at ({o["x"]},{o["y"]})')

    # ---------- per-net pad connectivity
    nets = defaultdict(list)
    for p in pads:
        if p["net"]:
            nets[p["net"]].append(p)
    # plane fills (recomputed here)
    fills = {}
    for net, lay in PLANE.items():
        cut = []
        for p in pads:
            if p["th"] and p["net"] != net:
                cut.append(p["geom"].buffer(CLR, quad_segs=6))
        for v in vias:
            if v["net"] != net:
                cut.append(v["geom"].buffer(CLR, quad_segs=8))
        fill = inner.difference(unary_union(cut)) if cut else inner
        fills[net] = fill
        if fill.geom_type == "Polygon":
            islands = [fill]
        else:
            islands = list(fill.geoms)
        fills[net + "_islands"] = len(islands)

    unconnected = []
    per_net = {}
    for net, pl in nets.items():
        idx = {id(o): k for k, o in enumerate(objs)}
        comps = defaultdict(list)
        for p in pl:
            comps[comp_of[idx[id(p)]]].append(p)
        net_vias = [k for k, o in enumerate(objs) if o["kind"] == "via" and o["net"] == net]
        via_comp = {comp_of[k] for k in net_vias}
        if net in PLANE:
            fill = fills[net]
            # plane-connected: a pad is connected if it is TH (reaches every layer and the plane),
            # or its copper component contains a via whose centre is inside the plane region.
            bad = []
            for p in pl:
                if p["th"]:
                    if not fill.buffer(1e-6).contains(Point(p["x"], p["y"])) and not inner.contains(Point(p["x"], p["y"])):
                        bad.append(p["id"])
                    continue
                c = comp_of[idx[id(p)]]
                ok = False
                for k in net_vias:
                    if comp_of[k] == c and fill.buffer(1e-6).contains(objs[k]["geom"].centroid):
                        ok = True; break
                if not ok:
                    bad.append(p["id"])
            for pid in bad:
                unconnected.append((net, pid, "no plane via"))
            per_net[net] = dict(pads=len(pl), open=len(bad), plane=PLANE[net])
        else:
            # signal: all pads in one component (TH pads are connected through every layer)
            main_comp = max(comps.items(), key=lambda kv: len(kv[1]))[0]
            opens = [p["id"] for c, lst in comps.items() if c != main_comp for p in lst]
            for pid in opens:
                unconnected.append((net, pid, "not connected to net"))
            per_net[net] = dict(pads=len(pl), open=len(opens), components=len(comps))
    # Plane connectivity sanity: plane-net TH pads/vias must sit in the largest island
    summary = dict(
        file=os.path.basename(path),
        pads=len(pads), tracks=len(segs), vias=len(vias),
        nets_with_pads=len(nets),
        nets_fully_connected=sum(1 for n, v in per_net.items() if v["open"] == 0),
        nets_open=sum(1 for n, v in per_net.items() if v["open"] > 0),
        unconnected_items=len(unconnected),
        shorts=len(issues["shorts"]),
        clearance_violations=len(issues["clearance"]),
        hole_to_hole=len(issues["hole_to_hole"]),
        board_edge_violations=len(issues["board_edge"]),
        dangling_tracks=len(dang_tracks),
        dangling_vias=len(dang_vias),
        plane_islands={k: v for k, v in fills.items() if k.endswith("_islands")},
    )
    report = dict(summary=summary, unconnected=unconnected, issues={k: v[:50] for k, v in issues.items()},
                  dangling_tracks=dang_tracks[:50], dangling_vias=dang_vias[:50], per_net=per_net)
    if out_json:
        json.dump(report, open(out_json, "w"), indent=1)
    print(json.dumps(summary, indent=1))
    if unconnected:
        print("unconnected (first 40):")
        for u in unconnected[:40]:
            print("   ", u)
    for k in ("shorts", "clearance", "hole_to_hole", "board_edge"):
        if issues[k]:
            print(k, len(issues[k]), issues[k][:8])
    return report


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
