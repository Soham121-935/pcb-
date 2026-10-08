#!/usr/bin/env python3
"""
SV16 Rev A - grid-based 4-layer autorouter (draft, not signed off).

Input : sv16_board_placed_native.kicad_pcb  (placement only, 0 copper)
Output: sv16_board_routed_draft.kicad_pcb    (tracks, vias, GND/3V3 plane zones)
        routing/sv16_routes.json             (every connection that was routed)
        routing/sv16_design_rules.json       (rules used)

Layer model (from the handoff):
    F.Cu    signals / FPGA fanout        -> routed here
    In1.Cu  GND plane                    -> zone, reached by through-vias
    In2.Cu  3V3 plane                    -> zone, reached by through-vias
    B.Cu    signals                      -> routed here

Rules used:
    signal track 0.15 mm, power track 0.30 mm, clearance 0.15 mm,
    via 0.50 mm / drill 0.25 mm, copper-to-edge 0.30 mm, hole-to-hole 0.25 mm.

Rotation convention (KiCad, Y axis down, angle CCW on screen):
    x' = x*cos + y*sin ;  y' = -x*sin + y*cos
    Pad angles in the file are absolute (they already include the footprint angle).

Requires: numpy, shapely 2.2.0.
Usage: route_sv16.py <src.kicad_pcb> <dst.kicad_pcb> <out_dir>
"""
import heapq, json, math, os, sys, time, uuid
import numpy as np
import shapely
from shapely.geometry import box, Point
from shapely import affinity

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sexpr import parse, find, first, val  # noqa: E402

SRC = sys.argv[1] if len(sys.argv) > 1 else "sv16_board_placed_native.kicad_pcb"
DST = sys.argv[2] if len(sys.argv) > 2 else "sv16_board_routed_draft.kicad_pcb"
OUT = sys.argv[3] if len(sys.argv) > 3 else "routing"

# ---------------------------------------------------------------- rules (mm)
G = 0.10
CLR = 0.15
CLRM = CLR + 0.01     # router masks carry a 10 um margin (rounding safety)
SIG_W = 0.15
PWR_W = 0.30
VIA_D = 0.50
VIA_DR = 0.25
VIA_R = VIA_D / 2
EDGE = 0.30
VIA_COST = 3            # grid steps charged for a layer change
MAX_EXP = int(os.environ.get("SV16_MAX_EXP", "350000"))
PLANE_NETS = {"GND": "In1.Cu", "3V3": "In2.Cu"}
POWER_NETS = {"VM_IN", "VM_IN_RAW", "J9_VIN", "U5_SW", "U6_SW",
              "USB_VBUS", "5V_USB", "1V1", "2V5"}
PROBES = {0: SIG_W, 1: PWR_W}  # probe class -> width of the net being routed


def width_of(net):
    return PWR_W if net in POWER_NETS else SIG_W


def probe_of(net):
    return 1 if net in POWER_NETS else 0


def layer_idx(name):
    return 0 if name == "F.Cu" else 1


# ---------------------------------------------------------------- board model
def load_board(path):
    t = parse(open(path, encoding="utf-8").read())
    pads = []
    for f in find(t, "footprint"):
        at = first(f, "at")
        fx, fy = float(at[1][1]), float(at[2][1])
        fr = float(at[3][1]) if len(at) > 3 else 0.0
        ref = [val(x[2]) for x in find(f, "property") if val(x[1]) == "Reference"]
        ref = ref[0] if ref else "?"
        r = math.radians(fr)
        c, s = math.cos(r), math.sin(r)
        for p in find(f, "pad"):
            pn = val(p[1]); ptype = val(p[2]); shape = val(p[3])
            pat = first(p, "at")
            px, py = float(pat[1][1]), float(pat[2][1])
            pr = float(pat[3][1]) if len(pat) > 3 else 0.0
            sz = first(p, "size")
            w, h = float(sz[1][1]), float(sz[2][1])
            ax = fx + (px * c + py * s)
            ay = fy + (-px * s + py * c)
            n = first(p, "net")
            net = val(n[1]) if n else ""
            lay = first(p, "layers")
            raw = [val(x) for x in lay[1:]]
            layers = ["F.Cu", "B.Cu"] if "*.Cu" in raw else [l for l in raw if l.endswith(".Cu")]
            pads.append(dict(ref=ref, num=pn, type=ptype, shape=shape, x=ax, y=ay,
                             w=w, h=h, rot=pr + fr, net=net, layers=layers,
                             th=(ptype in ("thru_hole", "np_thru_hole")),
                             id=f"{ref}.{pn}", uid=len(pads)))
    return t, pads


def load_outline(t):
    xs, ys = [], []
    for gl in find(t, "gr_line"):
        if val(first(gl, "layer")[1]) != "Edge.Cuts":
            continue
        for k in ("start", "end"):
            q = first(gl, k)
            xs.append(float(q[1][1])); ys.append(float(q[2][1]))
    bnd = (min(xs), min(ys), max(xs), max(ys))
    return box(*bnd), bnd


def pad_polygon(p):
    if p["shape"] == "circle":
        return Point(p["x"], p["y"]).buffer(p["w"] / 2, quad_segs=8)
    g = box(-p["w"] / 2, -p["h"] / 2, p["w"] / 2, p["h"] / 2)
    # rotate by the absolute pad angle (shapely rotate is CCW in a y-up frame;
    # KiCad angles are CCW on screen, i.e. the same sense in board coordinates)
    g = affinity.rotate(g, p["rot"], origin=(0, 0))
    return affinity.translate(g, p["x"], p["y"])


# ---------------------------------------------------------------- grid
class Grid:
    def __init__(self, bnd):
        self.NX = int(math.ceil(bnd[2] / G)) + 1
        self.NY = int(math.ceil(bnd[3] / G)) + 1
        self.NXY = self.NX * self.NY
        shp = (self.NX, self.NY)
        self.shape = shp
        self.TB = {(p, L): np.zeros(shp, np.int16) for p in PROBES for L in (0, 1)}
        self.PB = {(p, L): np.zeros(shp, np.int16) for p in PROBES for L in (0, 1)}
        self.VB = np.zeros(shp, np.int16)      # via-centre obstacles from tracks/vias
        self.VP = np.zeros(shp, np.int16)      # via-centre obstacles from pads/edge
        self.PIN = np.zeros(shp, bool)         # pad interiors (no vias there)
        self._disk = {}

    def rasterize(self, geom):
        if geom.is_empty:
            return 0, 0, np.zeros((0, 0), bool)
        minx, miny, maxx, maxy = geom.bounds
        i0 = max(0, int(math.floor(minx / G)) - 1)
        j0 = max(0, int(math.floor(miny / G)) - 1)
        i1 = min(self.NX - 1, int(math.ceil(maxx / G)) + 1)
        j1 = min(self.NY - 1, int(math.ceil(maxy / G)) + 1)
        if i1 < i0 or j1 < j0:
            return 0, 0, np.zeros((0, 0), bool)
        ii = np.arange(i0, i1 + 1) * G
        jj = np.arange(j0, j1 + 1) * G
        X, Y = np.meshgrid(ii, jj, indexing="ij")
        return i0, j0, shapely.contains_xy(geom, X, Y)

    @staticmethod
    def add(arr, i0, j0, mask, sign=1):
        if mask.size == 0:
            return
        ni, nj = mask.shape
        a_i0, a_j0 = max(0, i0), max(0, j0)
        s_i0, s_j0 = a_i0 - i0, a_j0 - j0
        e_i = min(ni, arr.shape[0] - i0)
        e_j = min(nj, arr.shape[1] - j0)
        if e_i <= s_i0 or e_j <= s_j0:
            return
        sub = mask[s_i0:e_i, s_j0:e_j].astype(np.int16)
        arr[a_i0:a_i0 + sub.shape[0], a_j0:a_j0 + sub.shape[1]] += sign * sub

    def disk(self, r):
        key = round(r, 4)
        if key not in self._disk:
            R = int(math.ceil(r / G)) + 1
            ii, jj = np.meshgrid(np.arange(-R, R + 1), np.arange(-R, R + 1), indexing="ij")
            m = (ii * ii + jj * jj) * G * G <= r * r + 1e-9
            self._disk[key] = (m, -R, -R)
        return self._disk[key]

    def stamp_disk(self, arr, i, j, r, sign=1):
        m, di, dj = self.disk(r)
        self.add(arr, i + di, j + dj, m, sign)


def build_obstacles(grid, pads, edge_poly):
    # board edge: probe-width-dependent copper keep-out
    for p in PROBES:
        inner = edge_poly.buffer(-(EDGE + PROBES[p] / 2), quad_segs=4)
        ring = edge_poly.difference(inner)
        i0, j0, m = grid.rasterize(ring)
        for L in (0, 1):
            grid.add(grid.PB[(p, L)], i0, j0, m)
    inner_v = edge_poly.buffer(-(EDGE + VIA_R), quad_segs=4)
    i0, j0, m = grid.rasterize(edge_poly.difference(inner_v))
    grid.add(grid.VP, i0, j0, m)

    for pd in pads:
        poly = pad_polygon(pd)
        pd["poly"] = poly
        i0, j0, m = grid.rasterize(poly)
        pd["inner"] = (i0, j0, m)
        if m.size:
            sub = grid.PIN[max(0, i0):i0 + m.shape[0], max(0, j0):j0 + m.shape[1]]
            sub |= m[:sub.shape[0], :sub.shape[1]]
        for p in PROBES:
            i0, j0, m = grid.rasterize(poly.buffer(CLRM + PROBES[p] / 2, quad_segs=6))
            for L in (0, 1):
                if L in [layer_idx(l) for l in pd["layers"]]:
                    grid.add(grid.PB[(p, L)], i0, j0, m)
        i0, j0, m = grid.rasterize(poly.buffer(CLRM + VIA_R, quad_segs=6))
        grid.add(grid.VP, i0, j0, m)


# ---------------------------------------------------------------- router
DIRS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
        (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]


class Router:
    def __init__(self, grid, pads):
        self.g = grid
        self.pads = pads
        self.by_net = {}
        for pd in pads:
            if pd["net"]:
                self.by_net.setdefault(pd["net"], []).append(pd)
        self.stats = dict(expansions=0, searches=0)

    def node(self, L, i, j):
        return L * self.g.NXY + i * self.g.NY + j

    def decode(self, n):
        L, r = divmod(n, self.g.NXY)
        i, j = divmod(r, self.g.NY)
        return L, i, j

    def pad_nodes(self, pd):
        """Nodes inside a pad (on each of its layers); falls back to centre cell."""
        g = self.g
        i0, j0, m = pd["inner"]
        out = []
        if m.size:
            ii, jj = np.nonzero(m)
            for L in [layer_idx(l) for l in pd["layers"]]:
                for a, b in zip(ii, jj):
                    out.append(self.node(L, i0 + a, j0 + b))
        if not out:
            ci, cj = int(round(pd["x"] / G)), int(round(pd["y"] / G))
            for L in [layer_idx(l) for l in pd["layers"]]:
                out.append(self.node(L, ci, cj))
        return out

    def net_view(self, net):
        """Blocked arrays for `net`: other nets' copper + pads, own pads excluded."""
        g = self.g
        own = {(p, L): np.zeros(g.shape, np.int16) for p in PROBES for L in (0, 1)}
        ownvp = np.zeros(g.shape, np.int16)
        for pd in self.by_net.get(net, []):
            for p in PROBES:
                i0, j0, m = g.rasterize(pd["poly"].buffer(CLRM + PROBES[p] / 2, quad_segs=6))
                for L in [layer_idx(l) for l in pd["layers"]]:
                    g.add(own[(p, L)], i0, j0, m)
            i0, j0, m = g.rasterize(pd["poly"].buffer(CLRM + VIA_R, quad_segs=6))
            g.add(ownvp, i0, j0, m)
        blk = {k: (g.TB[k] + g.PB[k] - own[k]) > 0 for k in g.TB}
        viaok = ~(((g.VB + g.VP - ownvp) > 0) | g.PIN)
        return blk, viaok

    def astar(self, sources, goal_nodes, goal_xy, plane_mode, window, probe, blk, viaok):
        g = self.g
        NY, NXY = g.NY, g.NXY
        B = np.concatenate([blk[(probe, 0)].ravel(), blk[(probe, 1)].ravel()]).astype(np.uint8).tobytes()
        V = viaok.ravel().astype(np.uint8).tobytes()
        wi0, wj0, wi1, wj1 = window
        gi, gj = goal_xy if goal_xy else (0, 0)

        def h(i, j):
            if plane_mode:
                return 0.0
            dx = abs(i - gi); dy = abs(j - gj)
            return max(dx, dy) + 0.4142 * min(dx, dy)

        cnt = 0
        heap = []
        best = {}
        parent = {}
        for n in sources:
            if n in best:
                continue
            _, i, j = self.decode(n)
            best[n] = 0.0
            parent[n] = None
            heapq.heappush(heap, (h(i, j), 0.0, cnt, n, 0)); cnt += 1
        exp = 0
        found = None
        while heap:
            f, gc, _, n, flag = heapq.heappop(heap)
            if flag == 1:
                found = (n, "via"); break
            if best.get(n, 1e18) < gc - 1e-9:
                continue
            if not plane_mode and n in goal_nodes:
                found = (n, "pad"); break
            exp += 1
            if exp > MAX_EXP:
                break
            L, r = divmod(n, NXY)
            i, j = divmod(r, NY)
            if plane_mode and V[r] and parent.get(n) is not None:
                # via from this copper node down to the plane
                heapq.heappush(heap, (gc + VIA_COST, gc + VIA_COST, cnt, n, 1)); cnt += 1
            if not plane_mode and V[r]:
                n2 = (1 - L) * NXY + r
                ng = gc + VIA_COST
                if ng < best.get(n2, 1e18) - 1e-9:
                    best[n2] = ng; parent[n2] = n
                    heapq.heappush(heap, (ng + h(i, j), ng, cnt, n2, 0)); cnt += 1
            for di, dj, c in DIRS:
                ni, nj = i + di, j + dj
                if ni < wi0 or ni > wi1 or nj < wj0 or nj > wj1:
                    continue
                n2 = L * NXY + ni * NY + nj
                if B[n2]:
                    continue
                ng = gc + c
                if ng < best.get(n2, 1e18) - 1e-9:
                    best[n2] = ng; parent[n2] = n
                    heapq.heappush(heap, (ng + h(ni, nj), ng, cnt, n2, 0)); cnt += 1
        self.stats["expansions"] += exp
        self.stats["searches"] += 1
        if found is None:
            return None
        end, kind = found
        path = []
        cur = end
        while cur is not None:
            path.append(cur)
            cur = parent.get(cur)
        path.reverse()
        return path, kind

    def search(self, sources, goal_nodes, goal_xy, plane_mode, probe, blk, viaok):
        g = self.g
        NY, NXY = g.NY, g.NXY
        si = np.array([(n % NXY) // NY for n in sources]); sj = np.array([(n % NXY) % NY for n in sources])
        allI, allJ = si, sj
        if goal_nodes and not plane_mode:
            ti = np.array([(n % NXY) // NY for n in goal_nodes]); tj = np.array([(n % NXY) % NY for n in goal_nodes])
            allI = np.concatenate([si, ti]); allJ = np.concatenate([sj, tj])
        for margin in (80, g.NX):
            wi0 = max(0, int(allI.min()) - margin); wi1 = min(g.NX - 1, int(allI.max()) + margin)
            wj0 = max(0, int(allJ.min()) - margin); wj1 = min(g.NY - 1, int(allJ.max()) + margin)
            res = self.astar(sources, goal_nodes, goal_xy, plane_mode, (wi0, wj0, wi1, wj1), probe, blk, viaok)
            if res is not None:
                return res
            if margin == g.NX:
                break
        return None


def cells_to_polylines(path, router):
    """Node path -> list of (layer, [(i,j),...]) and list of via (i,j)."""
    tracks, vias = [], []
    cur_L = None; cur = []
    prev = None
    for n in path:
        L, i, j = router.decode(n)
        if prev is not None and L != prev[0] and (i, j) == (prev[1], prev[2]):
            vias.append((i, j))
            if cur:
                tracks.append((cur_L, cur))
            cur = [(i, j)]; cur_L = L
        else:
            if cur_L is None:
                cur_L = L
            if cur_L != L:
                tracks.append((cur_L, cur))
                cur = [(prev[1], prev[2])]
                cur_L = L
            if not cur or cur[-1] != (i, j):
                cur.append((i, j))
        prev = (L, i, j)
    if cur:
        tracks.append((cur_L, cur))
    return [t for t in tracks if len(t[1]) >= 1], vias


def simplify(points):
    if len(points) <= 2:
        return list(points)
    out = [points[0]]
    for k in range(1, len(points) - 1):
        a, b, c = out[-1], points[k], points[k + 1]
        if (b[0] - a[0], b[1] - a[1]) == (c[0] - b[0], c[1] - b[1]):
            continue
        out.append(b)
    out.append(points[-1])
    return out


def mm(p):
    return (round(p[0] * G, 4), round(p[1] * G, 4))


class Board:
    """Accumulates copper for the output file and stamps obstacles."""

    def __init__(self, grid):
        self.g = grid
        self.segments = []   # dict(net, layer, a, b, w)
        self.vias = []       # dict(net, x, y)

    def stamp(self, net, tracks, vias):
        g = self.g
        w = width_of(net)
        for L, cells in tracks:
            for (i, j) in cells:
                for p in PROBES:
                    g.stamp_disk(g.TB[(p, L)], i, j, w / 2 + CLRM + PROBES[p] / 2)
                g.stamp_disk(g.VB, i, j, VIA_R + CLRM + w / 2)
        for (i, j) in vias:
            for p in PROBES:
                for L in (0, 1):
                    g.stamp_disk(g.TB[(p, L)], i, j, VIA_R + CLRM + PROBES[p] / 2)
            g.stamp_disk(g.VB, i, j, VIA_D + CLRM)   # centre-to-centre >= 2*r + clr


def route_all(grid, pads, edge_poly, bnd, hint=None):
    R = Router(grid, pads)
    board = Board(grid)
    routes = {}
    failures = []
    t0 = time.time()

    # ---- net ordering
    def hpwl(net):
        xs = [p["x"] for p in R.by_net[net]]; ys = [p["y"] for p in R.by_net[net]]
        return (max(xs) - min(xs)) + (max(ys) - min(ys))

    nets = [n for n in R.by_net if len(R.by_net[n]) >= 2 or n in PLANE_NETS]
    fpga = {p["net"] for p in pads if p["ref"] == "U1" and p["net"]}
    order = []
    order += sorted([n for n in nets if n in POWER_NETS], key=hpwl)
    order += sorted([n for n in nets if n in PLANE_NETS], key=hpwl)
    order += sorted([n for n in nets if n not in POWER_NETS and n not in PLANE_NETS and n in fpga], key=hpwl)
    order += sorted([n for n in nets if n not in POWER_NETS and n not in PLANE_NETS and n not in fpga], key=hpwl)
    seed = os.environ.get('SV16_SEED')
    if seed:
        import random
        sig = [n for n in order if n not in POWER_NETS and n not in PLANE_NETS]
        random.Random(int(seed)).shuffle(sig)
        order = [n for n in order if n in POWER_NETS or n in PLANE_NETS] + sig
    if hint:
        order = [n for n in hint if n in order] + [n for n in order if n not in hint]

    for net in order:
        pn = R.by_net[net]
        probe = probe_of(net)
        rec = dict(net=net, width=width_of(net), connections=[], vias=[], unrouted=[],
                   plane=PLANE_NETS.get(net))
        if net in PLANE_NETS:
            # every SMD pad gets its own via to the plane
            for pd in pn:
                if pd["th"]:
                    rec["connections"].append(dict(pad=pd["id"], kind="through-hole pad (plane reached directly)", tracks=[], vias=[]))
                    continue
                blk, viaok = R.net_view(net)
                sources = R.pad_nodes(pd)
                res = R.search(sources, set(), None, True, probe, blk, viaok)
                if res is None:
                    rec["unrouted"].append(pd["id"]); failures.append((net, pd["id"]))
                    continue
                path, kind = res
                tracks, vias = cells_to_polylines(path, R)
                # the path's last node is the via location
                _, vi, vj = R.decode(path[-1])
                if (vi, vj) not in vias:
                    vias.append((vi, vj))
                # stub from pad centre to first routed cell
                board.stamp(net, tracks, vias)
                for L, cells in tracks:
                    board.segments.append(dict(net=net, L=L, pts=[mm(c) for c in simplify(cells)], w=width_of(net), pad=pd["id"]))
                for (i, j) in vias:
                    board.vias.append(dict(net=net, x=mm((i, j))[0], y=mm((i, j))[1]))
                rec["connections"].append(dict(pad=pd["id"], kind="via to " + PLANE_NETS[net],
                                               tracks=[dict(layer=("F.Cu" if L == 0 else "B.Cu"), points=[mm(c) for c in simplify(cells)]) for L, cells in tracks],
                                               vias=[mm(v) for v in vias]))
            routes[net] = rec
            continue

        # ---- tree routing for signal nets
        blk, viaok = R.net_view(net)
        first_pad = pn[0]
        connected = {first_pad["uid"]}
        open_uids = set()
        tree = set(R.pad_nodes(first_pad))
        pending_tracks, pending_vias = [], []
        pad_by_id = {p["id"]: p for p in pn}
        conn_log = []
        while True:
            rem = [p for p in pn if p["uid"] not in connected and p["uid"] not in open_uids]
            if not rem:
                break
            tree_arr = np.array([((n % grid.NXY) // grid.NY, (n % grid.NXY) % grid.NY) for n in tree], float)
            best_p, best_d = None, 1e18
            for p in rem:
                d = np.min(np.hypot(tree_arr[:, 0] - p["x"] / G, tree_arr[:, 1] - p["y"] / G))
                if d < best_d:
                    best_d, best_p = d, p
            pd = best_p
            goal = set(R.pad_nodes(pd))
            gxy = (int(round(pd["x"] / G)), int(round(pd["y"] / G)))
            res = R.search(list(tree), goal, gxy, False, probe, blk, viaok)
            if res is None:
                rec["unrouted"].append(pd["id"]); failures.append((net, pd["id"])); open_uids.add(pd["uid"])
                continue
            path, kind = res
            tracks, vias = cells_to_polylines(path, R)
            # stub from last routed cell to pad centre
            pending_tracks += tracks
            pending_vias += vias
            # tree grows
            tree |= set(path)
            for (i, j) in vias:
                tree.add(R.node(0, i, j)); tree.add(R.node(1, i, j))
            tree |= set(goal)
            connected.add(pd["uid"])
            conn_log.append(dict(to=pd["id"], tracks=[dict(layer=("F.Cu" if L == 0 else "B.Cu"),
                                                             points=[mm(c) for c in simplify(cells)]) for L, cells in tracks],
                                 vias=[mm(v) for v in vias]))
        # commit the net
        board.stamp(net, pending_tracks, pending_vias)
        for L, cells in pending_tracks:
            pts = [mm(c) for c in simplify(cells)]
            if len(pts) >= 2:
                board.segments.append(dict(net=net, L=L, pts=pts, w=width_of(net)))
        for (i, j) in pending_vias:
            board.vias.append(dict(net=net, x=mm((i, j))[0], y=mm((i, j))[1]))
        rec["connections"] = conn_log
        rec["vias"] = [mm(v) for v in pending_vias]
        routes[net] = rec
        status = "OK" if not rec["unrouted"] else f"PARTIAL ({len(rec['unrouted'])} pads open)"
        print(f"[{time.time()-t0:7.1f}s] {net:14s} pads={len(pn):3d} {status}", flush=True)

    return R, board, routes, failures


def build_plane_geometry(pads, board, edge_poly):
    """Plane fill as I compute it (used for verification and the report).

    An inner-layer plane is only cut by through-hole pads and vias of OTHER nets
    (SMD pads and F/B tracks do not exist on In1/In2)."""
    from shapely.ops import unary_union
    fills = {}
    for net in PLANE_NETS:
        holes = []
        for pd in pads:
            if pd["th"] and pd["net"] != net:
                holes.append(pd["poly"].buffer(CLR, quad_segs=6))
        for v in board.vias:
            if v["net"] != net:
                holes.append(Point(v["x"], v["y"]).buffer(VIA_R + CLR, quad_segs=8))
        region = edge_poly.buffer(-EDGE, quad_segs=4).difference(unary_union(holes))
        fills[net] = region
    return fills


def write_pcb(src_text, dst, board, fills, bnd):
    """Insert tracks, vias and plane zones before the closing parenthesis."""
    body = src_text.rstrip()
    assert body.endswith(")")
    body = body[:-1]
    out = []
    q = lambda s: '"' + s.replace('"', '\\"') + '"'
    for s in board.segments:
        layer = "F.Cu" if s["L"] == 0 else "B.Cu"
        pts = s["pts"]
        for a, b in zip(pts[:-1], pts[1:]):
            if a == b:
                continue
            out.append(f'\t(segment (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (width {s["w"]}) '
                       f'(layer {q(layer)}) (net {q(s["net"])}) (uuid {q(str(uuid.uuid4()))}))')
    for v in board.vias:
        out.append(f'\t(via (at {v["x"]} {v["y"]}) (size {VIA_D}) (drill {VIA_DR}) '
                   f'(layers "F.Cu" "B.Cu") (net {q(v["net"])}) (uuid {q(str(uuid.uuid4()))}))')
    x0, y0, x1, y1 = bnd
    outline = f"(polygon (pts (xy {x0} {y0}) (xy {x1} {y0}) (xy {x1} {y1}) (xy {x0} {y1})))"
    for net, lay in PLANE_NETS.items():
        out.append(f'\t(zone (net {q(net)}) (net_name {q(net)}) (layer {q(lay)}) (uuid {q(str(uuid.uuid4()))}) '
                   f'(name {q("PLANE_" + net)}) (hatch edge 0.5) '
                   f'(connect_pads (clearance {CLR})) (min_thickness 0.2) (filled_areas_thickness no) '
                   f'(fill yes (thermal_gap 0.3) (thermal_bridge_width 0.3)) {outline})')
    text = body + "\n" + "\n".join(out) + "\n)\n"
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    src_text = open(SRC, encoding="utf-8").read()
    t, pads = load_board(SRC)
    edge_poly, bnd = load_outline(t)
    best = None
    hint = None
    PASSES = int(os.environ.get("SV16_PASSES", "4"))
    for k in range(PASSES):
        grid = Grid(bnd)
        build_obstacles(grid, pads, edge_poly)
        print(f"=== pass {k+1}: grid {grid.NX}x{grid.NY} @ {G} mm, order hint={'yes' if hint else 'no'}", flush=True)
        R, board, routes, failures = route_all(grid, pads, edge_poly, bnd, hint)
        nfail = len(failures)
        print(f"=== pass {k+1}: failed pad connections = {nfail}", flush=True)
        if best is None or nfail < len(best[3]):
            best = (R, board, routes, failures, grid)
        if nfail == 0:
            break
        failed_nets = []
        for n, _ in failures:
            if n not in failed_nets:
                failed_nets.append(n)
        hint = failed_nets
    R, board, routes, failures, grid = best
    fills = build_plane_geometry(pads, board, edge_poly)
    write_pcb(src_text, DST, board, fills, bnd)

    rules = dict(grid_mm=G, signal_track_mm=SIG_W, power_track_mm=PWR_W, clearance_mm=CLR,
                 router_mask_margin_mm=CLRM - CLR,
                 via_diameter_mm=VIA_D, via_drill_mm=VIA_DR, edge_clearance_mm=EDGE,
                 plane_nets=PLANE_NETS, power_width_nets=sorted(POWER_NETS),
                 rotation_convention="x'=x*cos+y*sin ; y'=-x*sin+y*cos (KiCad)",
                 router="route_sv16.py grid A*, 8-direction, layer change cost %d, passes=%d" % (VIA_COST, PASSES))
    json.dump(rules, open(os.path.join(OUT, "sv16_design_rules.json"), "w"), indent=2)
    summary = dict(
        tracks=len(board.segments), vias=len(board.vias),
        nets_routed=sum(1 for r in routes.values() if not r["unrouted"]),
        nets_total=len(routes),
        failures=failures, stats=R.stats, seconds=round(time.time() - t0, 1))
    json.dump(dict(summary=summary, routes=routes), open(os.path.join(OUT, "sv16_routes.json"), "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in summary.items() if k != "failures"}, indent=1))
    print("failed connections:", len(failures))
    for f in failures:
        print("   ", f)


if __name__ == "__main__":
    main()
