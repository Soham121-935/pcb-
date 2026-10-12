#!/usr/bin/env python3
"""
SV16 negotiated-congestion (PathFinder-style) router.

Builds on route_sv16.py (same grid, rules, obstacle model and output writer).
Each iteration rips up and reroutes every net. Overlaps with other nets are soft
costs (present congestion + history), so nets can negotiate shared corridors.
Hard constraints kept: board edge, via legality (no via in/near foreign copper),
pad interiors for vias.  After each iteration the copper is checked for
clearance conflicts; cells with conflicts accumulate history cost.
The best iteration (fewest open pads + conflict cells) is written out.

Usage: route_sv16_negotiated.py <src.kicad_pcb> <dst.kicad_pcb> <out_dir>
Env:   SV16_ITERS (default 8)
"""
import json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import route_sv16 as R0  # noqa: E402
from route_sv16 import (G, CLR, CLRM, EDGE, VIA_R, VIA_D, VIA_DR, PROBES, POWER_NETS, PLANE_NETS,
                        Grid, Router, Board, build_obstacles, load_board, load_outline,
                        cells_to_polylines, simplify, mm, width_of, probe_of, layer_idx,
                        build_plane_geometry, write_pcb, DIRS, VIA_COST, pad_polygon)

SRC = sys.argv[1]
DST = sys.argv[2]
OUT = sys.argv[3]
ITERS = int(os.environ.get("SV16_ITERS", "8"))
HINC = 1.0


def stamp_into(TBd, VBd, grid, net, tracks, vias, sign=1, TBV=None):
    """Stamp copper of `net` into TB/VB dicts/arrays (sign +1 add, -1 remove).
    TBV (optional) receives via-only clearance stamps: these are hard constraints."""
    w = width_of(net)
    for L, cells in tracks:
        for (i, j) in cells:
            for p in PROBES:
                grid.stamp_disk(TBd[(p, L)], i, j, w / 2 + CLRM + PROBES[p] / 2, sign)
            grid.stamp_disk(VBd, i, j, VIA_R + CLRM + w / 2, sign)
    for (i, j) in vias:
        for p in PROBES:
            for L in (0, 1):
                grid.stamp_disk(TBd[(p, L)], i, j, VIA_R + CLRM + PROBES[p] / 2, sign)
                if TBV is not None:
                    grid.stamp_disk(TBV[(p, L)], i, j, VIA_R + CLRM + PROBES[p] / 2, sign)
        grid.stamp_disk(VBd, i, j, VIA_D + CLRM, sign)


def own_pad_arrays(grid, pads_of_net):
    """Pad clearance masks for one net's pads (per probe, per layer) and via masks."""
    PBo = {(p, L): np.zeros(grid.shape, np.int16) for p in PROBES for L in (0, 1)}
    VPo = np.zeros(grid.shape, np.int16)
    for pd in pads_of_net:
        for p in PROBES:
            i0, j0, m = grid.rasterize(pd["poly"].buffer(CLRM + PROBES[p] / 2, quad_segs=6))
            for L in [layer_idx(l) for l in pd["layers"]]:
                grid.add(PBo[(p, L)], i0, j0, m)
        i0, j0, m = grid.rasterize(pd["poly"].buffer(CLRM + VIA_R, quad_segs=6))
        grid.add(VPo, i0, j0, m)
    return PBo, VPo


class NegRouter(Router):
    """Router whose A* takes blk=(PEN, HARD) and viaok (bool array)."""

    def astar(self, sources, goal_nodes, goal_xy, plane_mode, window, probe, blk, viaok):
        PEN, HARD = blk
        g = self.g
        NY, NXY = g.NY, g.NXY
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
            heapq_push(heap, (h(i, j), 0.0, cnt, n, 0)); cnt += 1
        exp = 0
        found = None
        MAX = R0.MAX_EXP
        while heap:
            f, gc, _, n, flag = heapq_pop(heap)
            if flag == 1:
                found = (n, "via"); break
            if best.get(n, 1e18) < gc - 1e-9:
                continue
            if not plane_mode and n in goal_nodes:
                found = (n, "pad"); break
            exp += 1
            if exp > MAX:
                break
            L, r = divmod(n, NXY)
            i, j = divmod(r, NY)
            if plane_mode and V[r] and parent.get(n) is not None:
                heapq_push(heap, (gc + VIA_COST, gc + VIA_COST, cnt, n, 1)); cnt += 1
            if not plane_mode and V[r]:
                n2 = (1 - L) * NXY + r
                ng = gc + VIA_COST
                if ng < best.get(n2, 1e18) - 1e-9:
                    best[n2] = ng; parent[n2] = n
                    heapq_push(heap, (ng + h(i, j), ng, cnt, n2, 0)); cnt += 1
            for di, dj, c in DIRS:
                ni, nj = i + di, j + dj
                if ni < wi0 or ni > wi1 or nj < wj0 or nj > wj1:
                    continue
                n2 = L * NXY + ni * NY + nj
                if HARD[n2]:
                    continue
                ng = gc + c + float(PEN[n2])
                if ng < best.get(n2, 1e18) - 1e-9:
                    best[n2] = ng; parent[n2] = n
                    heapq_push(heap, (ng + h(ni, nj), ng, cnt, n2, 0)); cnt += 1
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


import heapq
heapq_push = heapq.heappush
heapq_pop = heapq.heappop


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    src_text = open(SRC, encoding="utf-8").read()
    t, pads = load_board(SRC)
    edge_poly, bnd = load_outline(t)
    # static hard edge mask per probe (both layers)
    ref_grid = Grid(bnd)
    HARD = {}
    for p in PROBES:
        inner = edge_poly.buffer(-(EDGE + PROBES[p] / 2), quad_segs=4)
        i0, j0, m = ref_grid.rasterize(edge_poly.difference(inner))
        arr = np.zeros(ref_grid.shape, bool)
        arr[i0:i0 + m.shape[0], j0:j0 + m.shape[1]] = m
        HARD[p] = np.concatenate([arr.ravel(), arr.ravel()]).astype(np.uint8).tobytes()
    edge_mask = {}
    for p in PROBES:
        edge_mask[p] = np.frombuffer(HARD[p], np.uint8)[: ref_grid.NXY].reshape(ref_grid.shape).astype(bool)
    hist = {L: np.zeros(ref_grid.shape, np.float32) for L in (0, 1)}

    by_net = {}
    for pd in pads:
        if pd["net"]:
            by_net.setdefault(pd["net"], []).append(pd)
    nets = [n for n in by_net if len(by_net[n]) >= 2 or n in PLANE_NETS]
    fpga = {p["net"] for p in pads if p["ref"] == "U1" and p["net"]}

    def hpwl(net):
        xs = [p["x"] for p in by_net[net]]; ys = [p["y"] for p in by_net[net]]
        return (max(xs) - min(xs)) + (max(ys) - min(ys))
    order = []
    order += sorted([n for n in nets if n in POWER_NETS], key=hpwl)
    order += sorted([n for n in nets if n in PLANE_NETS], key=hpwl)
    order += sorted([n for n in nets if n not in POWER_NETS and n not in PLANE_NETS and n in fpga], key=hpwl)
    order += sorted([n for n in nets if n not in POWER_NETS and n not in PLANE_NETS and n not in fpga], key=hpwl)

    prev = {}
    best = None
    history_log = []
    for it in range(ITERS):
        pres = 2.0 + it
        grid = Grid(bnd)
        build_obstacles(grid, pads, edge_poly)
        grid.TBV = {(p, L): np.zeros(grid.shape, np.int16) for p in PROBES for L in (0, 1)}
        R = NegRouter(grid, pads)
        # stamp copper of the previous iteration (all nets)
        for net, c in prev.items():
            stamp_into(grid.TB, grid.VB, grid, net, c["tracks"], c["vias"], +1, grid.TBV)
        new = {}
        failures = []
        for net in order:
            pn = by_net[net]
            probe = probe_of(net)
            probe_w = PROBES[probe]
            if net in prev:
                c = prev[net]
                stamp_into(grid.TB, grid.VB, grid, net, c["tracks"], c["vias"], -1)
            rec = dict(net=net, width=width_of(net), connections=[], vias=[], unrouted=[],
                       plane=PLANE_NETS.get(net))
            tracks_all, vias_all = [], []

            def view(own_vias=()):
                PBo, VPo = own_pad_arrays(grid, pn)
                occ = {k: (grid.TB[k] + grid.PB[k] - PBo[k]) for k in grid.TB}
                ownV = {k: np.zeros(grid.shape, np.int16) for k in grid.TBV}
                if own_vias:
                    stamp_into({(p, L): np.zeros(grid.shape, np.int16) for p in PROBES for L in (0, 1)},
                               np.zeros(grid.shape, np.int16), grid, net, [], list(own_vias), +1, ownV)
                hardv = {}
                for L in (0, 1):
                    hardv[L] = (grid.TBV[(probe, L)] - ownV[(probe, L)] + grid.PB[(probe, L)] - PBo[(probe, L)]) > 0
                hard_bytes = {}
                for p in PROBES:
                    m = {}
                    for L in (0, 1):
                        hv = (grid.TBV[(p, L)] - (ownV[(p, L)] if p == probe else 0) + grid.PB[(p, L)] - PBo[(p, L)]) > 0
                        m[L] = hv
                    arr0 = m[0] | edge_mask[p]; arr1 = m[1] | edge_mask[p]
                    hard_bytes[p] = np.concatenate([arr0.ravel(), arr1.ravel()]).astype(np.uint8).tobytes()
                viaok = ~(((grid.VB + grid.VP - VPo) > 0) | grid.PIN | (grid.TBV[(probe, 0)] - ownV[(probe, 0)] > 0))
                return occ, viaok, hard_bytes

            def pen_for(occ):
                parts = []
                for L in (0, 1):
                    o = np.maximum(occ[(probe, L)], 0).astype(np.float32)
                    parts.append((hist[L] + pres * o).ravel())
                return np.concatenate(parts).astype(np.float32)

            if net in PLANE_NETS:
                for pd in pn:
                    if pd["th"]:
                        rec["connections"].append(dict(pad=pd["id"], kind="through-hole pad (plane reached directly)", tracks=[], vias=[]))
                        continue
                    occ, viaok, hb = view(tuple(vias_all))
                    res = R.search(R.pad_nodes(pd), set(), None, True, probe, (pen_for(occ), hb[probe]), viaok)
                    if res is None:
                        rec["unrouted"].append(pd["id"]); failures.append((net, pd["id"]))
                        continue
                    path, _ = res
                    tr, vi = cells_to_polylines(path, R)
                    _, vi_i, vi_j = R.decode(path[-1])
                    if (vi_i, vi_j) not in vi:
                        vi.append((vi_i, vi_j))
                    # plane vias are stamped at once so the next pad's via keeps clear of them
                    stamp_into(grid.TB, grid.VB, grid, net, tr, vi, +1, grid.TBV)
                    tracks_all += tr; vias_all += vi
                    rec["connections"].append(dict(pad=pd["id"], kind="via to " + PLANE_NETS[net],
                                                   tracks=[dict(layer=("F.Cu" if L == 0 else "B.Cu"), points=[mm(c) for c in simplify(cells)]) for L, cells in tr],
                                                   vias=[mm(v) for v in vi]))
            else:
                occ, viaok, hb = view()
                PEN = pen_for(occ)
                first_pad = pn[0]
                connected = {first_pad["uid"]}
                tree = set(R.pad_nodes(first_pad))
                open_uids = set()
                conn_log = []
                while True:
                    rem = [p for p in pn if p["uid"] not in connected and p["uid"] not in open_uids]
                    if not rem:
                        break
                    tarr = np.array([((n % grid.NXY) // grid.NY, (n % grid.NXY) % grid.NY) for n in tree], float)
                    bp, bd = None, 1e18
                    for p in rem:
                        d = np.min(np.hypot(tarr[:, 0] - p["x"] / G, tarr[:, 1] - p["y"] / G))
                        if d < bd:
                            bd, bp = d, p
                    pd = bp
                    goal = set(R.pad_nodes(pd))
                    gxy = (int(round(pd["x"] / G)), int(round(pd["y"] / G)))
                    res = R.search(list(tree), goal, gxy, False, probe, (PEN, hb[probe]), viaok)
                    if res is None:
                        rec["unrouted"].append(pd["id"]); failures.append((net, pd["id"])); open_uids.add(pd["uid"])
                        continue
                    path, _ = res
                    tr, vi = cells_to_polylines(path, R)
                    tracks_all += tr; vias_all += vi
                    tree |= set(path)
                    for (i, j) in vi:
                        tree.add(R.node(0, i, j)); tree.add(R.node(1, i, j))
                    tree |= goal
                    connected.add(pd["uid"])
                    conn_log.append(dict(to=pd["id"], tracks=[dict(layer=("F.Cu" if L == 0 else "B.Cu"),
                                                                    points=[mm(c) for c in simplify(cells)]) for L, cells in tr],
                                         vias=[mm(v) for v in vi]))
                rec["connections"] = conn_log
                rec["vias"] = [mm(v) for v in vias_all]
                stamp_into(grid.TB, grid.VB, grid, net, tracks_all, vias_all, +1, grid.TBV)
            new[net] = dict(tracks=tracks_all, vias=vias_all, rec=rec)
        prev = new
        # ---- conflict check on the assembled copper
        conflicts = 0
        for net in order:
            c = prev[net]
            if not c["tracks"] and not c["vias"]:
                continue
            probe = probe_of(net)
            pn = by_net[net]
            own = {(p, L): np.zeros(grid.shape, np.int16) for p in PROBES for L in (0, 1)}
            ownV = np.zeros(grid.shape, np.int16)
            stamp_into(own, ownV, grid, net, c["tracks"], c["vias"], +1)
            PBo, _ = own_pad_arrays(grid, pn)
            for L in (0, 1):
                others = grid.TB[(probe, L)] - own[(probe, L)] + grid.PB[(probe, L)] - PBo[(probe, L)]
                m = (own[(probe, L)] > 0) & (others > 0)
                k = int(m.sum())
                if k:
                    conflicts += k
                    hist[L][m] += HINC
        nopen = len(failures)
        score = nopen + conflicts
        history_log.append(dict(iter=it + 1, open_pads=nopen, conflict_cells=conflicts,
                                seconds=round(time.time() - t0, 1)))
        print(f"=== iter {it+1}: open pads={nopen} conflict cells={conflicts} (t={time.time()-t0:.0f}s)", flush=True)
        if best is None or score < best[0]:
            best = (score, dict(prev), list(failures), R.stats)
        if score == 0:
            break

    score, sol, failures, stats = best
    # ---- write outputs from the best iteration
    grid = Grid(bnd)
    board = Board(grid)
    routes = {}
    for net, c in sol.items():
        for L, cells in c["tracks"]:
            pts = [mm(x) for x in simplify(cells)]
            if len(pts) >= 2:
                board.segments.append(dict(net=net, L=L, pts=pts, w=width_of(net)))
        for (i, j) in c["vias"]:
            board.vias.append(dict(net=net, x=mm((i, j))[0], y=mm((i, j))[1]))
        routes[net] = c["rec"]
    fills = build_plane_geometry(pads, board, edge_poly)
    write_pcb(src_text, DST, board, fills, bnd)
    rules = dict(grid_mm=G, signal_track_mm=R0.SIG_W, power_track_mm=R0.PWR_W, clearance_mm=CLR,
                 router_mask_margin_mm=CLRM - CLR, via_diameter_mm=VIA_D, via_drill_mm=VIA_DR,
                 edge_clearance_mm=EDGE, plane_nets=PLANE_NETS, power_width_nets=sorted(POWER_NETS),
                 rotation_convention="x'=x*cos+y*sin ; y'=-x*sin+y*cos (KiCad)",
                 router="route_sv16_negotiated.py: PathFinder-style negotiated congestion, iterations=%d" % len(history_log))
    json.dump(rules, open(os.path.join(OUT, "sv16_design_rules.json"), "w"), indent=2)
    summary = dict(tracks=len(board.segments), vias=len(board.vias),
                   nets_routed=sum(1 for r in routes.values() if not r["unrouted"]),
                   nets_total=len(routes), failures=failures, stats=stats,
                   iterations=history_log, seconds=round(time.time() - t0, 1))
    json.dump(dict(summary=summary, routes=routes), open(os.path.join(OUT, "sv16_routes.json"), "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("failures", "iterations")}, indent=1))
    print("best score", score, "open pads", len(failures))


if __name__ == "__main__":
    main()
