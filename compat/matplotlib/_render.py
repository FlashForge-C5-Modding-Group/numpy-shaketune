"""Numpy-only raster canvas: antialiased fills, strokes, glyph text, images and PNG read/write."""
import os
import struct
import zlib

import numpy as np

_FONT = None


def _font():
    global _FONT
    if _FONT is None:
        d = np.load(os.path.join(os.path.dirname(__file__), '_data', 'dejavu_outlines.npz'))
        chars = list(d['chars'])
        _FONT = {'index': {c: i for i, c in enumerate(chars)}}
        for w in ('normal', 'bold'):
            _FONT[w] = (d[w + '_pts'].astype(np.float64), d[w + '_contours'], d[w + '_glyphs'], d[w + '_adv'])
        pts, cont, gl, _ = _FONT['normal']
        idx = _FONT['index']
        # vertical metrics like matplotlib: height of 'lp' (ascent of l, descent of p)
        def ext(ch):
            i = idx[ch]
            a, b = cont[gl[i]], cont[gl[i + 1]]
            return pts[a:b, 1].min(), pts[a:b, 1].max()
        _FONT['ascent'] = ext('l')[1]
        _FONT['descent'] = -ext('p')[0]
    return _FONT


def _weight_key(weight):
    if isinstance(weight, (int, float)):
        return 'bold' if weight >= 600 else 'normal'
    return 'bold' if str(weight).lower() in ('bold', 'heavy', 'black', 'semibold', 'demibold', 'extra bold') else 'normal'


def text_width(s, size, weight='normal'):
    f = _font()
    _, _, _, adv = f[_weight_key(weight)]
    idx = f['index']
    return sum(adv[idx.get(c, idx['?'])] for c in s) * size


def text_metrics(size):
    f = _font()
    return f['ascent'] * size, f['descent'] * size


def text_polys(s, size, weight='normal'):
    """Glyph contours of s at the origin (baseline at y=0, y up), in the same units as size."""
    f = _font()
    pts, cont, gl, adv = f[_weight_key(weight)]
    idx = f['index']
    polys, x = [], 0.0
    for c in s:
        i = idx.get(c, idx['?'])
        for k in range(gl[i], gl[i + 1]):
            p = pts[cont[k]:cont[k + 1]]
            if len(p) > 2:
                polys.append(np.column_stack([p[:, 0] * size + x, p[:, 1] * size]))
        x += adv[i] * size
    return polys, x


class Canvas:
    def __init__(self, width, height, background=(1.0, 1.0, 1.0)):
        self.w, self.h = int(width), int(height)
        self.img = np.empty((self.h, self.w, 3), np.float32)
        self.img[:] = background

    # ---- compositing -----------------------------------------------------------------------------

    def _box(self, x0, y0, x1, y1, clip):
        x0, y0 = max(int(np.floor(x0)), 0), max(int(np.floor(y0)), 0)
        x1, y1 = min(int(np.ceil(x1)), self.w), min(int(np.ceil(y1)), self.h)
        if clip is not None:
            x0, y0 = max(x0, int(np.floor(clip[0]))), max(y0, int(np.floor(clip[1])))
            x1, y1 = min(x1, int(np.ceil(clip[2]))), min(y1, int(np.ceil(clip[3])))
        return x0, y0, x1, y1

    def blend(self, cov, x0, y0, rgb, alpha=1.0):
        if cov.size == 0:
            return
        a = (cov * alpha)[..., None].astype(np.float32)
        region = self.img[y0:y0 + cov.shape[0], x0:x0 + cov.shape[1]]
        region *= 1 - a
        region += a * np.asarray(rgb, np.float32)

    def blend_rgba(self, rgba, x0, y0, alpha=1.0):
        a = rgba[..., 3:4] * alpha
        region = self.img[y0:y0 + rgba.shape[0], x0:x0 + rgba.shape[1]]
        region *= 1 - a
        region += a * rgba[..., :3]

    # ---- polygons --------------------------------------------------------------------------------

    def coverage(self, polys, box, ss=3, rule='nonzero'):
        """Antialiased coverage of polygons (pixel coords, y down) over box=(x0,y0,x1,y1) integer pixels."""
        x0, y0, x1, y1 = box
        W, H = x1 - x0, y1 - y0
        cov = np.zeros((H, W), np.float32)
        if W <= 0 or H <= 0:
            return cov
        ax, ay, bx, by = [], [], [], []
        for p in polys:
            p = np.asarray(p, np.float64)
            if len(p) < 3:
                continue
            q = np.roll(p, -1, axis=0)
            ax.append(p[:, 0]); ay.append(p[:, 1]); bx.append(q[:, 0]); by.append(q[:, 1])
        if not ax:
            return cov
        ax, ay, bx, by = (np.concatenate(v) for v in (ax, ay, bx, by))
        keep = ay != by
        ax, ay, bx, by = ax[keep], ay[keep], bx[keep], by[keep]
        if ax.size == 0:
            return cov
        d = np.where(by > ay, 1, -1).astype(np.int16)
        ylo, yhi = np.minimum(ay, by), np.maximum(ay, by)
        slope = (bx - ax) / (by - ay)
        WS = W * ss
        chunk = max(ss, (2_000_000 // max(1, ax.size)) // ss * ss)
        chunk = min(chunk, 512 * ss)
        rows_total = H * ss
        for r0 in range(0, rows_total, chunk):
            r1 = min(rows_total, r0 + chunk)
            ys = y0 + (np.arange(r0, r1) + 0.5) / ss
            # only edges spanning this chunk
            sel = (yhi > ys[0]) & (ylo <= ys[-1])
            if not sel.any():
                continue
            e_ay, e_ax, e_s, e_d = ay[sel], ax[sel], slope[sel], d[sel]
            e_lo, e_hi = ylo[sel], yhi[sel]
            Y = ys[:, None]
            hit = (Y >= e_lo) & (Y < e_hi)
            ri, ei = np.nonzero(hit)
            if ri.size == 0:
                continue
            xs = e_ax[ei] + (ys[ri] - e_ay[ei]) * e_s[ei]
            col = np.ceil((xs - x0) * ss - 0.5).astype(np.intp)
            np.clip(col, 0, WS, out=col)
            delta = np.zeros((r1 - r0, WS + 1), np.int16)
            np.add.at(delta, (ri, col), e_d[ei])
            wind = np.cumsum(delta[:, :WS], axis=1)
            inside = (wind != 0) if rule == 'nonzero' else (wind % 2 != 0)
            n = (r1 - r0) // ss
            cov[r0 // ss:r0 // ss + n] = inside[:n * ss].reshape(n, ss, W, ss).mean(axis=(1, 3))
        return cov

    def fill_polys(self, polys, rgb, alpha=1.0, clip=None, ss=3, rule='nonzero'):
        polys = [np.asarray(p, np.float64) for p in polys if len(p) >= 3]
        polys = [p[np.isfinite(p).all(axis=1)] for p in polys]
        polys = [p for p in polys if len(p) >= 3]
        if not polys:
            return
        allp = np.concatenate(polys)
        box = self._box(allp[:, 0].min(), allp[:, 1].min(), allp[:, 0].max() + 1, allp[:, 1].max() + 1, clip)
        if box[2] <= box[0] or box[3] <= box[1]:
            return
        cov = self.coverage(polys, box, ss, rule)
        self.blend(cov, box[0], box[1], rgb, alpha)

    def rect(self, x0, y0, x1, y1, rgb, alpha=1.0, clip=None):
        xa, xb = sorted((x0, x1))
        ya, yb = sorted((y0, y1))
        self.fill_polys([np.array([[xa, ya], [xb, ya], [xb, yb], [xa, yb]])], rgb, alpha, clip, ss=2)

    # ---- strokes ---------------------------------------------------------------------------------

    def stroke(self, pts, width, rgb, alpha=1.0, clip=None, dashes=None, closed=False):
        """Polyline (N x 2 pixel coords) with antialiased width (px). NaN points split the line."""
        pts = np.asarray(pts, np.float64)
        if closed and len(pts) > 1:
            pts = np.vstack([pts, pts[:1]])
        finite = np.isfinite(pts).all(axis=1)
        if not finite.all():
            start = 0
            for i in np.nonzero(~finite)[0].tolist() + [len(pts)]:
                if i - start >= 2:
                    self.stroke(pts[start:i], width, rgb, alpha, clip, dashes)
                start = i + 1
            return
        if len(pts) < 2:
            return
        r = max(width, 0.5) / 2.0
        lo, hi = pts.min(axis=0) - r - 2, pts.max(axis=0) + r + 2
        box = self._box(lo[0], lo[1], hi[0], hi[1], clip)
        if box[2] <= box[0] or box[3] <= box[1]:
            return
        # keep only segments that touch the box (big zoomed-in curves)
        seg_a, seg_b = pts[:-1], pts[1:]
        smin, smax = np.minimum(seg_a, seg_b) - r - 1, np.maximum(seg_a, seg_b) + r + 1
        vis = (smax[:, 0] >= box[0]) & (smin[:, 0] <= box[2]) & (smax[:, 1] >= box[1]) & (smin[:, 1] <= box[3])
        if not vis.any():
            return
        seg_a, seg_b = seg_a[vis], seg_b[vis]
        L = np.hypot(*(seg_b - seg_a).T)
        cum0 = np.concatenate([[0.0], np.cumsum(np.hypot(*(pts[1:] - pts[:-1]).T))])[:-1][vis]
        step = 0.35 if not dashes else min(0.35, max(0.1, min(dashes) / 2))
        n = np.maximum(1, np.ceil(L / step).astype(np.intp))
        total = int(n.sum())
        if total > 4_000_000:   # absurdly long: subsample
            step *= total / 4_000_000
            n = np.maximum(1, np.ceil(L / step).astype(np.intp))
        seg_i = np.repeat(np.arange(len(L)), n)
        off = np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n)
        t = (off / np.repeat(n, n))
        P = seg_a[seg_i] + (seg_b - seg_a)[seg_i] * t[:, None]
        P = np.vstack([P, seg_b[-1:]])
        arc = np.concatenate([cum0[seg_i] + L[seg_i] * t, [cum0[-1] + L[-1]]])
        if dashes:
            dashes = [max(d - width, 0.36) if i % 2 == 0 else d + min(width, d) for i, d in enumerate(dashes)]
            period = float(sum(dashes))
            ph = np.mod(arc, period)
            on = np.zeros(len(P), bool)
            acc = 0.0
            for k, dl in enumerate(dashes):
                if k % 2 == 0:
                    on |= (ph >= acc) & (ph < acc + dl)
                acc += dl
            P = P[on]
            if len(P) == 0:
                return
        x0, y0, x1, y1 = box
        cov = np.zeros((y1 - y0, x1 - x0), np.float32)
        K = int(np.ceil(r + 1.0))
        oy, ox = np.mgrid[-K:K + 1, -K:K + 1]
        oy, ox = oy.ravel(), ox.ravel()
        cx = np.floor(P[:, 0]).astype(np.intp)
        cy = np.floor(P[:, 1]).astype(np.intp)
        # process in blocks to bound memory
        blk = max(1, 3_000_000 // len(ox))
        for s in range(0, len(P), blk):
            px, py = P[s:s + blk, 0:1], P[s:s + blk, 1:2]
            gx = cx[s:s + blk, None] + ox[None, :]
            gy = cy[s:s + blk, None] + oy[None, :]
            dist = np.hypot(gx + 0.5 - px, gy + 0.5 - py)
            c = np.clip(r + 0.5 - dist, 0.0, 1.0)
            m = (c > 0) & (gx >= x0) & (gx < x1) & (gy >= y0) & (gy < y1)
            if m.any():
                np.maximum.at(cov, (gy[m] - y0, gx[m] - x0), c[m].astype(np.float32))
        self.blend(cov, x0, y0, rgb, alpha)

    # ---- text ------------------------------------------------------------------------------------

    def text(self, x, y, s, size, rgb, alpha=1.0, weight='normal', ha='left', va='baseline', rotation=0.0,
             clip=None, rotation_mode='default'):
        """size in px; (x, y) pixel anchor; rotation degrees counter-clockwise. rotation_mode as in matplotlib:
        'default' aligns the rotated bounding box, 'anchor' aligns before rotating."""
        if rotation % 360 and rotation_mode == 'default':
            asc, desc = text_metrics(size)
            lines = str(s).split(chr(10))
            w = max(text_width(l, size, weight) for l in lines)
            hgt = (asc + desc) * (1 + 1.2 * (len(lines) - 1))
            th = np.deg2rad(rotation)
            c, sn = np.cos(th), np.sin(th)
            # unrotated block: left edge at 0, top at 0 (y up)
            corners = np.array([[0, 0], [w, 0], [w, -hgt], [0, -hgt]], np.float64)
            rx = corners[:, 0] * c - corners[:, 1] * sn
            ry = corners[:, 0] * sn + corners[:, 1] * c
            ax_ = {'left': rx.min(), 'right': rx.max()}.get(ha, (rx.min() + rx.max()) / 2)
            ay_ = {'top': ry.max(), 'bottom': ry.min()}.get(va, (ry.min() + ry.max()) / 2)
            return self.text(x - ax_, y + ay_, s, size, rgb, alpha, weight, 'left', 'top', rotation, clip, 'anchor')
        lines = str(s).split('\n')
        asc, desc = text_metrics(size)
        line_h = (asc + desc) * 1.2
        widths = [text_width(l, size, weight) for l in lines]
        block_w = max(widths) if widths else 0.0
        block_h = asc + desc + line_h * (len(lines) - 1)
        # block offsets in text space (y up, origin = anchor)
        if va in ('top',):
            top = 0.0
        elif va in ('center', 'center_baseline'):
            top = block_h / 2
        elif va == 'bottom':
            top = block_h
        else:   # baseline: anchor on first baseline
            top = asc
        polys = []
        for i, (line, lw) in enumerate(zip(lines, widths)):
            ps, _ = text_polys(line, size, weight)
            if ha == 'center':
                dx = -lw / 2 if len(lines) == 1 else -block_w / 2 + (block_w - lw) / 2
            elif ha == 'right':
                dx = -lw if len(lines) == 1 else -block_w + (block_w - lw)
            else:
                dx = 0.0
            dy = top - asc - i * line_h
            polys += [p + (dx, dy) for p in ps]
        if not polys:
            return
        th = np.deg2rad(rotation)
        c, sn = np.cos(th), np.sin(th)
        out = []
        for p in polys:
            xr = p[:, 0] * c - p[:, 1] * sn
            yr = p[:, 0] * sn + p[:, 1] * c
            out.append(np.column_stack([x + xr, y - yr]))
        self.fill_polys(out, rgb, alpha, clip, ss=4)

    # ---- images ----------------------------------------------------------------------------------

    def image(self, rgba, x0, y0, x1, y1, clip=None, interpolation='nearest', alpha=1.0):
        """Draw rgba (h, w, 4 float 0..1, row 0 = top) stretched over the pixel box."""
        box = self._box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), clip)
        if box[2] <= box[0] or box[3] <= box[1]:
            return
        h, w = rgba.shape[:2]
        bx0, by0, bx1, by1 = box
        u = ((np.arange(bx0, bx1) + 0.5) - x0) / (x1 - x0) * w - 0.5
        v = ((np.arange(by0, by1) + 0.5) - y0) / (y1 - y0) * h - 0.5
        up_x, up_y = abs(x1 - x0) / max(w, 1), abs(y1 - y0) / max(h, 1)
        smooth = interpolation == 'bilinear' or (interpolation == 'antialiased' and not (up_x >= 3 and up_y >= 3))
        if smooth:
            u0 = np.clip(np.floor(u).astype(int), 0, w - 1); u1 = np.clip(u0 + 1, 0, w - 1); fu = np.clip(u - u0, 0, 1)
            v0 = np.clip(np.floor(v).astype(int), 0, h - 1); v1 = np.clip(v0 + 1, 0, h - 1); fv = np.clip(v - v0, 0, 1)
            top = rgba[v0][:, u0] * (1 - fu)[None, :, None] + rgba[v0][:, u1] * fu[None, :, None]
            bot = rgba[v1][:, u0] * (1 - fu)[None, :, None] + rgba[v1][:, u1] * fu[None, :, None]
            out = top * (1 - fv)[:, None, None] + bot * fv[:, None, None]
        else:
            ui = np.clip(np.round(u).astype(int), 0, w - 1)
            vi = np.clip(np.round(v).astype(int), 0, h - 1)
            out = rgba[vi][:, ui]
        self.blend_rgba(out.astype(np.float32), bx0, by0, alpha)

    def to_rgba8(self):
        return (np.clip(self.img, 0, 1) * 255 + 0.5).astype(np.uint8)


# ---- PNG ---------------------------------------------------------------------------------------------

def write_png(path, rgb8, dpi=None):
    h, w = rgb8.shape[:2]
    ch = rgb8.shape[2] if rgb8.ndim == 3 else 1
    ctype = {1: 0, 3: 2, 4: 6}[ch]
    raw = np.empty((h, w * ch + 1), np.uint8)
    raw[:, 0] = 0
    raw[:, 1:] = rgb8.reshape(h, w * ch)

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)
    out = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, ctype, 0, 0, 0))
    if dpi:
        ppm = int(round(dpi / 0.0254))
        out += chunk(b'pHYs', struct.pack('>IIB', ppm, ppm, 1))
    out += chunk(b'IDAT', zlib.compress(raw.tobytes(), 6)) + chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(out)


def read_png(path):
    """8-bit (palette/gray/RGB/RGBA, non-interlaced) PNG -> float32 array (h, w, 3|4) in 0..1."""
    with open(path, 'rb') as f:
        data = f.read()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not a PNG file')
    pos, idat, plte, trns = 8, [], None, None
    while pos < len(data):
        n, kind = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if kind == b'IHDR':
            w, h, depth, ctype, _, _, interlace = struct.unpack('>IIBBBBB', body)
        elif kind == b'PLTE':
            plte = np.frombuffer(body, np.uint8).reshape(-1, 3)
        elif kind == b'tRNS':
            trns = np.frombuffer(body, np.uint8)
        elif kind == b'IDAT':
            idat.append(body)
        pos += 12 + n
    if depth != 8 or interlace:
        raise ValueError('only 8-bit non-interlaced PNGs are supported')
    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    stride = w * ch
    raw = np.frombuffer(zlib.decompress(b''.join(idat)), np.uint8).reshape(h, stride + 1)
    out = np.zeros((h, stride), np.int32)
    prev = np.zeros(stride, np.int32)
    for y in range(h):
        ft, line = raw[y, 0], raw[y, 1:].astype(np.int32)
        if ft == 0:
            cur = line
        elif ft == 2:
            cur = (line + prev) & 255
        else:
            cur = np.zeros(stride, np.int32)
            for i in range(stride):
                a = cur[i - ch] if i >= ch else 0
                b = prev[i]
                if ft == 1:
                    p = a
                elif ft == 3:
                    p = (a + b) >> 1
                else:
                    c = prev[i - ch] if i >= ch else 0
                    pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                    p = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                cur[i] = (line[i] + p) & 255
        out[y] = cur
        prev = cur
    img = out.reshape(h, w, ch).astype(np.uint8)
    if ctype == 3:
        rgb = plte[img[..., 0]]
        a = np.full((h, w, 1), 255, np.uint8)
        if trns is not None:
            lut = np.full(len(plte), 255, np.uint8); lut[:len(trns)] = trns
            a = lut[img[..., 0]][..., None]
        img = np.concatenate([rgb, a], axis=2)
    elif ctype == 0:
        img = np.repeat(img, 3, axis=2)
    elif ctype == 4:
        img = np.concatenate([np.repeat(img[..., :1], 3, axis=2), img[..., 1:2]], axis=2)
    return img.astype(np.float32) / 255.0
