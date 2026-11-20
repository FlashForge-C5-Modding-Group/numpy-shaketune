"""matplotlib.axes subset rendered with numpy: cartesian, polar and simple 3D axes, legends, tables."""
import math

import numpy as np

from . import colors as mcolors
from . import ticker
from ._render import text_metrics, text_width
from .font_manager import FontProperties, size_points

LINESTYLES = {'-': None, 'solid': None, '--': (3.7, 1.6), 'dashed': (3.7, 1.6), ':': (1.0, 1.65),
              'dotted': (1.0, 1.65), '-.': (6.4, 1.6, 1.0, 1.6), 'dashdot': (6.4, 1.6, 1.0, 1.6)}
NOLINE = ('', ' ', 'None', 'none')
MARKERS = set('o.x+*sd^v<>|_D,')
GRID_DEFAULT = '#b0b0b0'
UPSIDE_DOWN_LOGO = True


def parse_fmt(fmt):
    color = marker = None
    linestyle = None
    s = fmt
    for ls in ('--', '-.', '-', ':'):
        if ls in s:
            linestyle = ls
            s = s.replace(ls, '', 1)
            break
    for ch in list(s):
        if ch in MARKERS and marker is None:
            marker = ch
        elif ch in 'bgrcmykw' and color is None:
            color = ch
    if s.strip() == '' and fmt.strip() == '' and fmt != '':
        return None, None, ' '
    if linestyle is None:
        linestyle = ' ' if marker else '-'
    return color, marker, linestyle


class Bbox:
    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0, self.x1, self.y1 = float(x0), float(y0), float(x1), float(y1)

    @property
    def width(self):
        return self.x1 - self.x0

    @property
    def height(self):
        return self.y1 - self.y0

    @property
    def bounds(self):
        return (self.x0, self.y0, self.width, self.height)

    @staticmethod
    def from_bounds(x0, y0, w, h):
        return Bbox(x0, y0, x0 + w, y0 + h)

    def __iter__(self):
        return iter(self.bounds)


class _Axis:
    def __init__(self):
        self.visible = True
        self.minor = False
        self.minor_ndivs = None
        self.sci = False
        self.scilimits = (0, 0)
        self.label = ''
        self.label_color = 'black'
        self.tick_color = 'black'
        self.tick_label_color = 'black'
        self.tick_label_size = 10.0

    def set_visible(self, b):
        self.visible = bool(b)

    def set_minor_locator(self, loc):
        self.minor = True
        self.minor_ndivs = getattr(loc, 'ndivs', None)

    def set_major_locator(self, loc):
        pass

    def set_major_formatter(self, fmt):
        pass

    def set_label_position(self, pos):
        pass

    def tick_left(self):
        pass

    def tick_right(self):
        pass

    def set_ticks_position(self, pos):
        pass


class Text:
    def __init__(self, s='', **kw):
        self.s = str(s)
        self.color = kw.get('color', 'black')
        self.fontsize = kw.get('fontsize', None)
        self.weight = kw.get('weight', 'normal')
        self.ha = kw.get('ha', 'center')
        self.va = kw.get('va', 'center')

    def set_color(self, c):
        self.color = c

    def set_fontproperties(self, fp):
        if isinstance(fp, FontProperties):
            self.weight = fp.get_weight()
            if fp._size is not None:
                self.fontsize = fp.get_size_in_points()

    def set_fontsize(self, s):
        self.fontsize = s

    def set_text(self, s):
        self.s = str(s)

    def get_text(self):
        return self.s


def _text_kw(kw, default_ha='left', default_va='baseline'):
    return {
        'ha': kw.get('ha', kw.get('horizontalalignment', default_ha)),
        'va': kw.get('va', kw.get('verticalalignment', default_va)),
        'size': size_points(kw.get('fontsize', kw.get('size'))),
        'weight': kw.get('weight', kw.get('fontweight', 'normal')),
        'color': kw.get('color', kw.get('c', 'black')),
        'alpha': kw.get('alpha', 1.0) if kw.get('alpha') is not None else 1.0,
        'rotation': float(kw.get('rotation', 0) or 0) if not isinstance(kw.get('rotation'), str) else
        (90.0 if kw.get('rotation') == 'vertical' else 0.0),
    }


class Cell:
    def __init__(self, text, fontsize):
        self._text = Text(text, fontsize=fontsize)
        self.edgecolor = 'black'
        self.facecolor = 'white'
        self.linewidth = 1.0
        self.alpha = 1.0

    def get_text(self):
        return self._text

    def set_text_props(self, **kw):
        t = self._text
        if 'ha' in kw or 'horizontalalignment' in kw:
            t.ha = kw.get('ha', kw.get('horizontalalignment'))
        if 'va' in kw or 'verticalalignment' in kw:
            t.va = kw.get('va', kw.get('verticalalignment'))
        if 'color' in kw:
            t.color = kw['color']
        if 'fontweight' in kw or 'weight' in kw:
            t.weight = kw.get('fontweight', kw.get('weight'))
        if 'fontproperties' in kw:
            t.set_fontproperties(kw['fontproperties'])

    def set_edgecolor(self, c):
        self.edgecolor = c

    def set_linewidth(self, w):
        self.linewidth = w

    def set_facecolor(self, c):
        self.facecolor = c

    def set_alpha(self, a):
        self.alpha = 1.0 if a is None else float(a)

    def set_height(self, h):
        pass

    def set_width(self, w):
        pass


class Table:
    PAD = 0.1

    def __init__(self, ax, cellText, colLabels=None, bbox=None, cellLoc='center', colWidths=None, **kw):
        self.ax = ax
        self.fontsize = 10.0
        self.zorder = 0
        self.bbox = bbox or [0, 0, 1, 1]
        self.colWidths = colWidths
        self.auto_cols = set()
        self._cells = {}
        rows = ([list(colLabels)] if colLabels is not None else []) + [list(r) for r in cellText]
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self._cells[(r, c)] = Cell(val, None)
                self._cells[(r, c)]._text.ha = 'center' if cellLoc == 'center' else cellLoc
        self.nrows = len(rows)
        self.ncols = max((len(r) for r in rows), default=0)

    def auto_set_font_size(self, value=True):
        pass

    def set_fontsize(self, size):
        self.fontsize = float(size)

    def auto_set_column_width(self, col):
        cols = col if isinstance(col, (list, tuple, range)) else [col]
        self.auto_cols.update(int(c) for c in cols)

    def set_zorder(self, z):
        self.zorder = z

    def get_celld(self):
        return self._cells

    def scale(self, xscale, yscale):
        pass


class Legend:
    def __init__(self, ax, handles, loc, fontsize, title=None):
        self.ax, self.handles, self.loc, self.fontsize = ax, handles, loc, fontsize


class Axes:
    name = 'rectilinear'

    def __init__(self, fig, position, sharex=None):
        self.figure = fig
        self._pos = Bbox.from_bounds(*position)
        self._anchor = 'C'
        self.xaxis, self.yaxis = _Axis(), _Axis()
        self._xlim = None
        self._ylim = None
        self._datalim = [np.inf, -np.inf, np.inf, -np.inf]
        self._artists = []
        self._order = 0
        self._cycle = 0
        self._title = None
        self._grid = {}
        self._legend = None
        self._axis_on = True
        self._patch_visible = True
        self._sharex = sharex
        self._ylabel_right = False
        self._aspect = 'auto'
        self._image_aspect = None
        self.zorder = 0

    # ---- positions -------------------------------------------------------------------------------

    def get_position(self, original=False):
        return Bbox(self._pos.x0, self._pos.y0, self._pos.x1, self._pos.y1)

    def set_position(self, pos, which='both'):
        if isinstance(pos, Bbox):
            self._pos = Bbox(pos.x0, pos.y0, pos.x1, pos.y1)
        else:
            self._pos = Bbox.from_bounds(*pos)

    def get_subplotspec(self):
        return getattr(self, '_subplotspec', None)

    def remove(self):
        self.figure.delaxes(self)

    def axis(self, arg=None):
        if arg in ('off', False):
            self._axis_on = False
        elif arg in ('on', True):
            self._axis_on = True
        return (0, 1, 0, 1)

    def set_axis_off(self):
        self._axis_on = False

    def set_aspect(self, aspect, **kw):
        self._aspect = aspect

    def set_facecolor(self, c):
        pass

    def set_zorder(self, z):
        self.zorder = z

    # ---- limits / labels -------------------------------------------------------------------------

    def _update_datalim(self, x=None, y=None):
        if x is not None:
            x = np.asarray(x, np.float64).ravel()
            x = x[np.isfinite(x)]
            if x.size:
                self._datalim[0] = min(self._datalim[0], x.min())
                self._datalim[1] = max(self._datalim[1], x.max())
        if y is not None:
            y = np.asarray(y, np.float64).ravel()
            y = y[np.isfinite(y)]
            if y.size:
                self._datalim[2] = min(self._datalim[2], y.min())
                self._datalim[3] = max(self._datalim[3], y.max())

    @staticmethod
    def _lim_arg(a, b):
        if b is None and isinstance(a, (list, tuple, np.ndarray)):
            a, b = a[0], a[1]
        return a, b

    def set_xlim(self, left=None, right=None, **kw):
        left, right = self._lim_arg(left, right)
        if self._sharex is not None:
            return self._sharex.set_xlim(left, right)
        cur = self.get_xlim()
        self._xlim = (float(cur[0] if left is None else left), float(cur[1] if right is None else right))
        return self._xlim

    def set_ylim(self, bottom=None, top=None, **kw):
        bottom, top = self._lim_arg(bottom, top)
        cur = self.get_ylim()
        self._ylim = (float(cur[0] if bottom is None else bottom), float(cur[1] if top is None else top))
        return self._ylim

    def _auto(self, lo, hi, margin=0.05):
        if not np.isfinite(lo) or not np.isfinite(hi):
            return (0.0, 1.0)
        if hi == lo:
            d = abs(lo) * 0.05 or 0.05
            return (lo - d, hi + d)
        pad = (hi - lo) * margin
        return (lo - pad, hi + pad)

    def get_xlim(self):
        if self._sharex is not None:
            return self._sharex.get_xlim()
        if self._xlim is not None:
            return self._xlim
        if self._image_aspect is not None:
            return self._image_aspect[0]
        lo, hi = self._datalim[0], self._datalim[1]
        for child in self.figure._axes:
            if getattr(child, '_sharex', None) is self:
                lo, hi = min(lo, child._datalim[0]), max(hi, child._datalim[1])
        return self._auto(lo, hi)

    def get_ylim(self):
        if self._ylim is not None:
            return self._ylim
        if self._image_aspect is not None:
            return self._image_aspect[1]
        return self._auto(self._datalim[2], self._datalim[3])

    def set_xlabel(self, s, **kw):
        self.xaxis.label = str(s)

    def set_ylabel(self, s, **kw):
        self.yaxis.label = str(s)

    def set_title(self, s, fontsize=None, color='black', weight='normal', fontweight=None, loc='center', pad=6.0, **kw):
        self._title = {'s': str(s), 'size': size_points(fontsize, 12.0), 'color': color,
                       'weight': fontweight or weight, 'pad': pad}

    def grid(self, visible=None, which='major', axis='both', color=None, linewidth=None, linestyle=None, **kw):
        if visible is False:
            for w in (('major', 'minor') if which == 'both' else (which,)):
                self._grid.pop(w, None)
            return
        for w in (('major', 'minor') if which == 'both' else (which,)):
            self._grid[w] = {'color': color or GRID_DEFAULT, 'lw': linewidth or 0.8,
                             'dashes': LINESTYLES.get(linestyle) if linestyle else None}

    def ticklabel_format(self, axis='both', style='', scilimits=None, **kw):
        for a in ((self.xaxis, self.yaxis) if axis == 'both' else (self.xaxis if axis == 'x' else self.yaxis,)):
            if style in ('sci', 'scientific'):
                a.sci = True
                a.scilimits = tuple(scilimits) if scilimits is not None else (-5, 6)
            elif style == 'plain':
                a.sci = False

    def tick_params(self, axis='both', which='major', colors=None, labelsize=None, labelcolor=None, color=None, **kw):
        for a in ((self.xaxis, self.yaxis) if axis == 'both' else (self.xaxis if axis == 'x' else self.yaxis,)):
            if colors is not None:
                a.tick_color = a.tick_label_color = colors
            if labelcolor is not None:
                a.tick_label_color = labelcolor
            if color is not None:
                a.tick_color = color
            if labelsize is not None:
                a.tick_label_size = size_points(labelsize)

    def twinx(self):
        ax2 = Axes(self.figure, self._pos.bounds, sharex=self)
        ax2._ylabel_right = True
        ax2.xaxis.set_visible(False)
        ax2._patch_visible = False
        ax2._parent = self
        self.figure._add_axes(ax2)
        return ax2

    # ---- artists ---------------------------------------------------------------------------------

    def _add(self, kind, zorder, **data):
        self._order += 1
        self._artists.append({'kind': kind, 'zorder': zorder, 'order': self._order, **data})
        return self._artists[-1]

    def _next_color(self):
        c = mcolors.CYCLE[self._cycle % len(mcolors.CYCLE)]
        self._cycle += 1
        return c

    def plot(self, *args, **kw):
        lines = []
        args = list(args)
        while args:
            if len(args) >= 2 and not isinstance(args[1], str):
                x, y = args[0], args[1]
                args = args[2:]
            else:
                y = args[0]
                x = np.arange(len(np.atleast_1d(y)))
                args = args[1:]
            fmt = None
            if args and isinstance(args[0], str):
                fmt = args.pop(0)
            fcolor, fmarker, fls = parse_fmt(fmt) if fmt is not None else (None, None, None)
            color = kw.get('color', kw.get('c', fcolor))
            if color is None:
                color = self._next_color()
            marker = kw.get('marker', fmarker)
            ls = kw.get('linestyle', kw.get('ls', fls if fls is not None else '-'))
            if ls in NOLINE and fmt is not None and fls == ' ' and marker is None:
                ls = ' '
            x = np.asarray(x, np.float64).ravel()
            y = np.asarray(y, np.float64).ravel()
            if x.size == 1 and y.size > 1:
                x = np.full(y.size, x[0])
            self._update_datalim(x, y)
            lines.append(self._add('line', kw.get('zorder', 2), x=x, y=y, color=color, alpha=kw.get('alpha', 1.0),
                                   lw=kw.get('linewidth', kw.get('lw', 1.5)), ls=ls, marker=marker,
                                   ms=kw.get('markersize', kw.get('ms', 6.0)), label=kw.get('label'),
                                   mfc=kw.get('markerfacecolor', color)))
        return lines

    def scatter(self, x, y, s=None, c=None, color=None, marker='o', alpha=None, edgecolors=None, linewidths=None,
                zorder=1, label=None, **kw):
        x = np.atleast_1d(np.asarray(x, np.float64))
        y = np.atleast_1d(np.asarray(y, np.float64))
        self._update_datalim(x, y)
        col = color if color is not None else (c if c is not None else self._next_color())
        return self._add('scatter', zorder, x=x, y=y, s=36.0 if s is None else s, color=col,
                         alpha=1.0 if alpha is None else alpha, edge=edgecolors, elw=linewidths or 1.0, label=label)

    def fill_between(self, x, y1, y2=0, color=None, alpha=None, label=None, zorder=1, facecolor=None, **kw):
        x = np.asarray(x, np.float64)
        y1 = np.broadcast_to(np.asarray(y1, np.float64), x.shape)
        y2 = np.broadcast_to(np.asarray(y2, np.float64), x.shape)
        self._update_datalim(x, np.concatenate([y1, y2]))
        col = color or facecolor or self._next_color()
        poly = np.column_stack([np.concatenate([x, x[::-1]]), np.concatenate([y1, y2[::-1]])])
        return self._add('poly', zorder, poly=poly, color=col, alpha=1.0 if alpha is None else alpha, label=label)

    def fill_betweenx(self, y, x1, x2=0, color=None, alpha=None, label=None, zorder=1, facecolor=None, **kw):
        y = np.asarray(y, np.float64)
        x1 = np.broadcast_to(np.asarray(x1, np.float64), y.shape)
        x2 = np.broadcast_to(np.asarray(x2, np.float64), y.shape)
        self._update_datalim(np.concatenate([x1, x2]), y)
        col = color or facecolor or self._next_color()
        poly = np.column_stack([np.concatenate([x1, x2[::-1]]), np.concatenate([y, y[::-1]])])
        return self._add('poly', zorder, poly=poly, color=col, alpha=1.0 if alpha is None else alpha, label=label)

    def fill(self, x, y, color=None, alpha=None, label=None, zorder=1, **kw):
        x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
        self._update_datalim(x, y)
        return self._add('poly', zorder, poly=np.column_stack([x, y]), color=color or self._next_color(),
                         alpha=1.0 if alpha is None else alpha, label=label)

    def axvline(self, x=0, ymin=0, ymax=1, color='black', linestyle='-', linewidth=1.5, alpha=1.0, zorder=2,
                label=None, **kw):
        color = kw.get('c', color)
        self._update_datalim(x=[x])
        return self._add('vline', zorder, x=float(x), ymin=ymin, ymax=ymax, color=color,
                         ls=kw.get('ls', linestyle), lw=kw.get('lw', linewidth), alpha=alpha, label=label)

    def axhline(self, y=0, xmin=0, xmax=1, color='black', linestyle='-', linewidth=1.5, alpha=1.0, zorder=2,
                label=None, **kw):
        color = kw.get('c', color)
        self._update_datalim(y=[y])
        return self._add('hline', zorder, y=float(y), xmin=xmin, xmax=xmax, color=color,
                         ls=kw.get('ls', linestyle), lw=kw.get('lw', linewidth), alpha=alpha, label=label)

    def axvspan(self, xmin, xmax, ymin=0, ymax=1, color=None, alpha=None, zorder=1, label=None, facecolor=None, **kw):
        self._update_datalim(x=[xmin, xmax])
        return self._add('vspan', zorder, x0=float(xmin), x1=float(xmax), color=color or facecolor or 'C0',
                         alpha=1.0 if alpha is None else alpha, label=label)

    def text(self, x, y, s, transform=None, **kw):
        return self._add('text', kw.get('zorder', 3), x=float(x), y=float(y), s=str(s), coords='data',
                         **_text_kw(kw))

    def annotate(self, text, xy, xytext=None, textcoords=None, xycoords='data', annotation_clip=None, **kw):
        tk = _text_kw(kw)
        return self._add('annot', kw.get('zorder', 3), s=str(text), xy=(float(xy[0]), float(xy[1])),
                         xytext=xytext, textcoords=textcoords or xycoords, xycoords=xycoords,
                         clip=annotation_clip, **tk)

    def legend(self, *args, loc='best', prop=None, fontsize=None, title=None, **kw):
        size = prop.get_size_in_points() if isinstance(prop, FontProperties) else size_points(fontsize)
        if isinstance(prop, dict):
            size = size_points(prop.get('size'))
        handles = [a for a in self._artists if a.get('label') and not str(a['label']).startswith('_')]
        self._legend = Legend(self, handles, loc, size, title)
        return self._legend

    def get_legend_handles_labels(self):
        h = [a for a in self._artists if a.get('label') and not str(a['label']).startswith('_')]
        return h, [a['label'] for a in h]

    def table(self, cellText=None, colLabels=None, bbox=None, loc=None, cellLoc='center', colWidths=None, **kw):
        t = Table(self, cellText or [], colLabels, bbox, cellLoc, colWidths)
        self._add('table', 0, table=t)
        return t

    def imshow(self, X, cmap=None, norm=None, aspect=None, extent=None, origin='upper', interpolation=None,
               vmin=None, vmax=None, alpha=None, zorder=0, **kw):
        a = np.asarray(X)
        if a.ndim == 2:
            norm = norm or mcolors.Normalize(vmin, vmax)
            rgba = mcolors.apply_cmap(norm(a), cmap or 'inferno')
        else:
            rgba = a.astype(np.float32)
            if rgba.max() > 1.0:
                rgba = rgba / 255.0
            if rgba.shape[2] == 3:
                rgba = np.concatenate([rgba, np.ones(rgba.shape[:2] + (1,), np.float32)], axis=2)
        h, w = rgba.shape[:2]
        if origin == 'lower':
            rgba = rgba[::-1]
        if extent is None:
            extent = (-0.5, w - 0.5, h - 0.5, -0.5) if origin == 'upper' else (-0.5, w - 0.5, -0.5, h - 0.5)
        l, r, b, t = (float(v) for v in extent)
        if aspect in (None, 'equal'):
            self._aspect = 'equal'
        self._image_aspect = ((l, r), (b, t))
        return self._add('image', zorder, rgba=rgba, extent=(l, r, b, t), origin=origin, picture=a.ndim == 3,
                         interp=interpolation or 'antialiased', alpha=1.0 if alpha is None else alpha)

    # ---- drawing ---------------------------------------------------------------------------------

    def _box_px(self, R):
        W, H = R.w, R.h
        x0, y0 = self._pos.x0 * W, (1 - self._pos.y1) * H
        x1, y1 = self._pos.x1 * W, (1 - self._pos.y0) * H
        if self._aspect == 'equal' and self._image_aspect is not None:
            (l, r), (b, t) = self.get_xlim(), self.get_ylim()
            dw, dh = abs(r - l), abs(t - b)
            bw, bh = x1 - x0, y1 - y0
            if dw > 0 and dh > 0:
                s = min(bw / dw, bh / dh)
                nw, nh = dw * s, dh * s
                if self._anchor and 'W' in self._anchor:
                    nx0 = x0
                elif self._anchor and 'E' in self._anchor:
                    nx0 = x1 - nw
                else:
                    nx0 = x0 + (bw - nw) / 2
                if self._anchor and 'N' in self._anchor:
                    ny0 = y0
                elif self._anchor and 'S' in self._anchor:
                    ny0 = y1 - nh
                else:
                    ny0 = y0 + (bh - nh) / 2
                x0, y0, x1, y1 = nx0, ny0, nx0 + nw, ny0 + nh
        return x0, y0, x1, y1

    def _transform(self, R):
        x0, y0, x1, y1 = self._box_px(R)
        xl, xh = self.get_xlim()
        yl, yh = self.get_ylim()
        sx = (x1 - x0) / ((xh - xl) or 1.0)
        sy = (y1 - y0) / ((yh - yl) or 1.0)
        tx = lambda v: x0 + (np.asarray(v, np.float64) - xl) * sx
        ty = lambda v: y1 - (np.asarray(v, np.float64) - yl) * sy
        return tx, ty, (x0, y0, x1, y1)

    def draw(self, R):
        tx, ty, box = self._transform(R)
        x0, y0, x1, y1 = box
        clip = box
        if self._patch_visible and self._axis_on:
            R.canvas.rect(x0, y0, x1, y1, (1, 1, 1))
        items = self._sorted_with_legend()
        grid_drawn = False
        for a in items:
            if not grid_drawn and a['zorder'] >= 1.5:
                self._draw_grid(R, tx, ty, box)
                grid_drawn = True
            if a['kind'] == 'legend':
                self._draw_legend(R, box)
            else:
                self._draw_artist(R, a, tx, ty, box, clip)
        if not grid_drawn:
            self._draw_grid(R, tx, ty, box)
        if self._axis_on:
            self._draw_frame(R, tx, ty, box)

    def _pt(self, R, v):
        return v * R.dpi / 72.0

    def _sorted_with_legend(self):
        items = list(self._artists)
        if self._legend is not None:
            items.append({'kind': 'legend', 'zorder': 5, 'order': 10 ** 9})
        return sorted(items, key=lambda a: (a['zorder'], a['order']))

    def _draw_grid(self, R, tx, ty, box):
        if not self._grid or not self._axis_on:
            return
        x0, y0, x1, y1 = box
        for which in ('minor', 'major'):
            g = self._grid.get(which)
            if not g:
                continue
            rgb = mcolors.to_rgb(g['color'])
            lw = self._pt(R, g['lw'])
            dashes = [self._pt(R, d * g['lw']) for d in g['dashes']] if g['dashes'] else None
            xs, ys = self._ticks(R, box, which)
            if self.xaxis.visible or self._sharex is None:
                for v in xs:
                    p = float(tx(v))
                    R.canvas.stroke([[p, y0], [p, y1]], lw, rgb, 1.0, box, dashes)
            for v in ys:
                p = float(ty(v))
                R.canvas.stroke([[x0, p], [x1, p]], lw, rgb, 1.0, box, dashes)

    def _ticks(self, R, box, which='major'):
        x0, y0, x1, y1 = box
        out = []
        for axis, lo_hi, length_px, is_x in ((self.xaxis, self.get_xlim(), x1 - x0, True),
                                              (self.yaxis, self.get_ylim(), y1 - y0, False)):
            lo, hi = sorted(lo_hi)
            size = axis.tick_label_size
            space = (length_px * 72.0 / R.dpi) / (size * (3.0 if is_x else 2.0))
            nbins = int(np.clip(space, 1, 9))
            major, step = ticker.nice_ticks(lo, hi, nbins)
            if which == 'major':
                out.append(major)
            else:
                out.append(ticker.minor_ticks(major, step, lo, hi, axis.minor_ndivs) if axis.minor else np.array([]))
        return out

    def _major_info(self, R, box):
        x0, y0, x1, y1 = box
        info = []
        for axis, lim, length_px, is_x in ((self.xaxis, self.get_xlim(), x1 - x0, True),
                                            (self.yaxis, self.get_ylim(), y1 - y0, False)):
            lo, hi = sorted(lim)
            space = (length_px * 72.0 / R.dpi) / (axis.tick_label_size * (3.0 if is_x else 2.0))
            major, step = ticker.nice_ticks(lo, hi, int(np.clip(space, 1, 9)))
            labels, offset = ticker.format_ticks(major, step, axis.sci, axis.scilimits)
            info.append((major, step, labels, offset))
        return info

    def _draw_frame(self, R, tx, ty, box):
        x0, y0, x1, y1 = box
        cv = R.canvas
        lw = self._pt(R, 0.8)
        black = (0, 0, 0)
        cv.stroke([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], lw, black, closed=True)
        (xmaj, xstep, xlab, xoff), (ymaj, ystep, ylab, yoff) = self._major_info(R, box)
        xmin_t, ymin_t = self._ticks(R, box, 'minor')
        maj_len, min_len, pad = self._pt(R, 3.5), self._pt(R, 2.0), self._pt(R, 3.5)
        label_bottom = y1
        if self.xaxis.visible:
            tc = mcolors.to_rgb(self.xaxis.tick_color)
            for v in xmin_t:
                p = float(tx(v)); cv.stroke([[p, y1], [p, y1 + min_len]], self._pt(R, 0.6), tc)
            fs = self._pt(R, self.xaxis.tick_label_size)
            asc, desc = text_metrics(fs)
            lc = mcolors.to_rgb(self.xaxis.tick_label_color)
            for v, s in zip(xmaj, xlab):
                p = float(tx(v))
                cv.stroke([[p, y1], [p, y1 + maj_len]], lw, tc)
                cv.text(p, y1 + maj_len + pad, s, fs, lc, ha='center', va='top')
            label_bottom = y1 + maj_len + pad + asc + desc
            if xoff:
                cv.text(x1, label_bottom, xoff, fs, lc, ha='right', va='top')
            if self.xaxis.label:
                cv.text((x0 + x1) / 2, label_bottom + self._pt(R, 4.0), self.xaxis.label, self._pt(R, 10), black,
                        ha='center', va='top')
        if self.yaxis.visible:
            right = self._ylabel_right
            tc = mcolors.to_rgb(self.yaxis.tick_color)
            lc = mcolors.to_rgb(self.yaxis.tick_label_color)
            fs = self._pt(R, self.yaxis.tick_label_size)
            sign = 1 if right else -1
            xe = x1 if right else x0
            for v in ymin_t:
                p = float(ty(v)); cv.stroke([[xe, p], [xe + sign * min_len, p]], self._pt(R, 0.6), tc)
            maxw = 0.0
            for v, s in zip(ymaj, ylab):
                p = float(ty(v))
                cv.stroke([[xe, p], [xe + sign * maj_len, p]], lw, tc)
                cv.text(xe + sign * (maj_len + pad), p, s, fs, lc, ha='left' if right else 'right', va='center_baseline')
                maxw = max(maxw, text_width(s, fs))
            if yoff:
                cv.text(x1 if right else x0, y0 - self._pt(R, 2.0), yoff, fs, lc, ha='right' if right else 'left',
                        va='bottom')
            if self.yaxis.label:
                lx = xe + sign * (maj_len + pad + maxw + self._pt(R, 4.0))
                cv.text(lx, (y0 + y1) / 2, self.yaxis.label, self._pt(R, 10), black, ha='center',
                        va='bottom' if not right else 'top', rotation=90, rotation_mode='anchor')
        if self._title:
            t = self._title
            ty0 = y0 - self._pt(R, t['pad'])
            if yoff and not self._ylabel_right:
                ty0 -= 0
            cv.text((x0 + x1) / 2, ty0, t['s'], self._pt(R, t['size']), mcolors.to_rgb(t['color']), weight=t['weight'],
                    ha='center', va='baseline')

    def _line_style(self, R, ls, lw):
        if ls in NOLINE:
            return None, False
        pat = LINESTYLES.get(ls)
        dashes = [self._pt(R, d * lw) for d in pat] if pat else None
        return dashes, True

    def _draw_marker(self, R, cx, cy, marker, ms, rgb, alpha, clip, mfc=None):
        cv = R.canvas
        s = self._pt(R, ms)
        if marker == 'x':
            h = s / 2
            for ax_, ay_, bx_, by_ in ((-h, -h, h, h), (-h, h, h, -h)):
                cv.stroke([[cx + ax_, cy + ay_], [cx + bx_, cy + by_]], self._pt(R, 1.0), rgb, alpha, clip)
        elif marker == '+':
            h = s / 2
            cv.stroke([[cx - h, cy], [cx + h, cy]], self._pt(R, 1.0), rgb, alpha, clip)
            cv.stroke([[cx, cy - h], [cx, cy + h]], self._pt(R, 1.0), rgb, alpha, clip)
        elif marker in ('o', '.', ','):
            r = s / 2 if marker == 'o' else s / 4
            th = np.linspace(0, 2 * np.pi, 24, endpoint=False)
            poly = np.column_stack([cx + r * np.cos(th), cy + r * np.sin(th)])
            cv.fill_polys([poly], mcolors.to_rgb(mfc) if mfc is not None else rgb, alpha, clip, ss=4)
            cv.stroke(poly, self._pt(R, 1.0), rgb, alpha, clip, closed=True)
        elif marker in ('s', 'D', 'd', '^', 'v', '<', '>', '*'):
            r = s / 2
            if marker == 's':
                poly = [[cx - r, cy - r], [cx + r, cy - r], [cx + r, cy + r], [cx - r, cy + r]]
            elif marker in ('D', 'd'):
                poly = [[cx, cy - r], [cx + r, cy], [cx, cy + r], [cx - r, cy]]
            else:
                ang = {'^': 90, 'v': -90, '<': 180, '>': 0, '*': 90}[marker]
                th = np.deg2rad(ang + np.array([0, 120, 240]))
                poly = np.column_stack([cx + r * np.cos(th), cy - r * np.sin(th)])
            cv.fill_polys([np.asarray(poly, float)], rgb, alpha, clip, ss=4)

    def _draw_artist(self, R, a, tx, ty, box, clip):
        cv = R.canvas
        k = a['kind']
        x0, y0, x1, y1 = box
        if k == 'line':
            rgb = mcolors.to_rgb(a['color'])
            px, py = tx(a['x']), ty(a['y'])
            dashes, on = self._line_style(R, a['ls'], a['lw'])
            if on and len(px) > 1:
                cv.stroke(np.column_stack([px, py]), self._pt(R, a['lw']), rgb, a['alpha'], clip, dashes)
            if a['marker']:
                for cx, cy in zip(px, py):
                    if np.isfinite(cx) and np.isfinite(cy):
                        self._draw_marker(R, cx, cy, a['marker'], a['ms'], rgb, a['alpha'], clip, a.get('mfc'))
        elif k == 'scatter':
            rgb = mcolors.to_rgb(a['color'])
            s = np.broadcast_to(np.asarray(a['s'], np.float64), a['x'].shape)
            for cx, cy, ss in zip(tx(a['x']), ty(a['y']), s):
                r = self._pt(R, math.sqrt(ss) / 2)
                th = np.linspace(0, 2 * np.pi, 28, endpoint=False)
                poly = np.column_stack([cx + r * np.cos(th), cy + r * np.sin(th)])
                cv.fill_polys([poly], rgb, a['alpha'], clip, ss=4)
                if a['edge'] is not None:
                    cv.stroke(poly, self._pt(R, a['elw']), mcolors.to_rgb(a['edge']), a['alpha'], clip, closed=True)
        elif k == 'poly':
            p = a['poly']
            cv.fill_polys([np.column_stack([tx(p[:, 0]), ty(p[:, 1])])], mcolors.to_rgb(a['color']), a['alpha'], clip)
        elif k == 'vline':
            p = float(tx(a['x']))
            dashes, on = self._line_style(R, a['ls'], a['lw'])
            if on:
                cv.stroke([[p, y1 - (y1 - y0) * a['ymin']], [p, y1 - (y1 - y0) * a['ymax']]], self._pt(R, a['lw']),
                          mcolors.to_rgb(a['color']), a['alpha'], clip, dashes)
        elif k == 'hline':
            p = float(ty(a['y']))
            dashes, on = self._line_style(R, a['ls'], a['lw'])
            if on:
                cv.stroke([[x0 + (x1 - x0) * a['xmin'], p], [x0 + (x1 - x0) * a['xmax'], p]], self._pt(R, a['lw']),
                          mcolors.to_rgb(a['color']), a['alpha'], clip, dashes)
        elif k == 'vspan':
            cv.rect(float(tx(a['x0'])), y0, float(tx(a['x1'])), y1, mcolors.to_rgb(a['color']), a['alpha'], clip)
        elif k == 'image':
            l, r, b, t = a['extent']
            rgba = a['rgba'][::-1] if a.get('picture') and UPSIDE_DOWN_LOGO else a['rgba']
            cv.image(rgba, float(tx(l)), float(ty(t)), float(tx(r)), float(ty(b)), clip,
                     'bilinear' if a['interp'] in ('bilinear',) else a['interp'], a['alpha'])
        elif k == 'text':
            cv.text(float(tx(a['x'])), float(ty(a['y'])), a['s'], self._pt(R, a['size']), mcolors.to_rgb(a['color']),
                    a['alpha'], a['weight'], a['ha'], a['va'], a['rotation'])
        elif k == 'annot':
            xa, ya = float(tx(a['xy'][0])), float(ty(a['xy'][1]))
            if a['clip'] in (None, True) and a['xycoords'] == 'data':
                if not (x0 - 0.5 <= xa <= x1 + 0.5 and y0 - 0.5 <= ya <= y1 + 0.5):
                    return
            if a['xytext'] is None:
                px, py = xa, ya
            elif a['textcoords'] == 'offset points':
                px, py = xa + self._pt(R, a['xytext'][0]), ya - self._pt(R, a['xytext'][1])
            elif a['textcoords'] == 'axes fraction':
                px, py = x0 + (x1 - x0) * a['xytext'][0], y1 - (y1 - y0) * a['xytext'][1]
            else:
                px, py = float(tx(a['xytext'][0])), float(ty(a['xytext'][1]))
            cv.text(px, py, a['s'], self._pt(R, a['size']), mcolors.to_rgb(a['color']), a['alpha'], a['weight'],
                    a['ha'], a['va'], a['rotation'])
        elif k == 'table':
            self._draw_table(R, a['table'], box)

    def _draw_table(self, R, t, box):
        x0, y0, x1, y1 = box
        cv = R.canvas
        bx, by, bw, bh = t.bbox
        fx0 = x0 + bx * (x1 - x0)
        fx1 = fx0 + bw * (x1 - x0)
        fy1 = y1 - by * (y1 - y0)
        fy0 = fy1 - bh * (y1 - y0)
        fs = self._pt(R, t.fontsize)
        widths = []
        for c in range(t.ncols):
            if t.colWidths is not None:
                widths.append(float(t.colWidths[c]))
            else:
                tw = max((text_width(cell.get_text().s, fs, cell.get_text().weight)
                          for (r, cc), cell in t._cells.items() if cc == c), default=fs)
                widths.append(tw / (1 - 2 * Table.PAD) if c in t.auto_cols else fs * 6)
        tot = sum(widths) or 1.0
        xs = [fx0]
        for w in widths:
            xs.append(xs[-1] + w / tot * (fx1 - fx0))
        rh = (fy1 - fy0) / max(1, t.nrows)
        for (r, c), cell in t._cells.items():
            cx0, cx1 = xs[c], xs[c + 1]
            cy0, cy1 = fy0 + r * rh, fy0 + (r + 1) * rh
            if cell.facecolor not in (None, 'none'):
                cv.rect(cx0, cy0, cx1, cy1, mcolors.to_rgb(cell.facecolor), cell.alpha)
            cv.stroke([[cx0, cy0], [cx1, cy0], [cx1, cy1], [cx0, cy1]], self._pt(R, cell.linewidth),
                      mcolors.to_rgb(cell.edgecolor), cell.alpha, closed=True)
            tt = cell.get_text()
            size = self._pt(R, tt.fontsize) if tt.fontsize else fs
            if tt.ha == 'left':
                px = cx0 + (cx1 - cx0) * Table.PAD
            elif tt.ha == 'right':
                px = cx1 - (cx1 - cx0) * Table.PAD
            else:
                px = (cx0 + cx1) / 2
            cv.text(px, (cy0 + cy1) / 2, tt.s, size, mcolors.to_rgb(tt.color), weight=tt.weight, ha=tt.ha,
                    va='center_baseline')

    def _draw_legend(self, R, box):
        lg = self._legend
        if not lg.handles:
            return
        cv = R.canvas
        x0, y0, x1, y1 = box
        fs = self._pt(R, lg.fontsize)
        asc, desc = text_metrics(fs)
        th = asc + desc
        pad, spacing, hl, htp, bap = 0.4 * fs, 0.5 * fs, 2.0 * fs, 0.8 * fs, 0.5 * fs
        rowh = max(th, 0.7 * fs)
        tw = max(text_width(str(h['label']), fs) for h in lg.handles)
        w = pad * 2 + hl + htp + tw
        h = pad * 2 + rowh * len(lg.handles) + spacing * (len(lg.handles) - 1)
        loc = lg.loc if isinstance(lg.loc, str) else 'upper right'
        if loc in ('best',):
            loc = 'upper right'
        lx = x0 + bap if 'left' in loc else (x1 - bap - w if 'right' in loc else (x0 + x1 - w) / 2)
        ly = y0 + bap if 'upper' in loc else (y1 - bap - h if 'lower' in loc else (y0 + y1 - h) / 2)
        cv.rect(lx, ly, lx + w, ly + h, (1, 1, 1), 0.8)
        cv.stroke([[lx, ly], [lx + w, ly], [lx + w, ly + h], [lx, ly + h]], self._pt(R, 1.0), (0.8, 0.8, 0.8),
                  0.8, closed=True)
        for i, a in enumerate(lg.handles):
            cy = ly + pad + i * (rowh + spacing) + rowh / 2
            hx0, hx1 = lx + pad, lx + pad + hl
            rgb = mcolors.to_rgb(a.get('color', 'black'))
            alpha = a.get('alpha', 1.0) or 1.0
            if a['kind'] in ('line', 'vline', 'hline'):
                dashes, on = self._line_style(R, a['ls'], a['lw'])
                if on:
                    cv.stroke([[hx0, cy], [hx1, cy]], self._pt(R, a['lw']), rgb, alpha, None, dashes)
                if a.get('marker'):
                    self._draw_marker(R, (hx0 + hx1) / 2, cy, a['marker'], a['ms'], rgb, alpha, None, a.get('mfc'))
            elif a['kind'] in ('poly', 'vspan'):
                cv.rect(hx0, cy - 0.35 * fs, hx1, cy + 0.35 * fs, rgb, alpha)
            elif a['kind'] == 'scatter':
                self._draw_marker(R, (hx0 + hx1) / 2, cy, 'o', math.sqrt(36.0), rgb, alpha, None)
            cv.text(hx1 + htp, cy, str(a['label']), fs, (0, 0, 0), ha='left', va='center_baseline')


class PolarAxes(Axes):
    name = 'polar'

    def __init__(self, fig, position):
        super().__init__(fig, position)
        self._theta_offset = 0.0
        self._theta_dir = 1
        self._thetagrids = list(range(0, 360, 45))
        self._xlim = (0.0, 2 * np.pi)
        self._grid = {'major': {'color': GRID_DEFAULT, 'lw': 0.8, 'dashes': None}}

    def set_theta_zero_location(self, loc, offset=0.0):
        self._theta_offset = np.deg2rad({'N': 90, 'NW': 135, 'W': 180, 'SW': 225, 'S': 270, 'SE': 315, 'E': 0,
                                         'NE': 45}[loc] + offset)

    def set_theta_direction(self, direction):
        self._theta_dir = 1 if direction in (1, 'counterclockwise', 'anticlockwise') else -1

    def set_thetagrids(self, angles, labels=None, **kw):
        self._thetagrids = [float(a) for a in angles]

    def set_rlabel_position(self, value):
        pass

    def get_ylim(self):
        if self._ylim is not None:
            return self._ylim
        hi = self._datalim[3]
        if not np.isfinite(hi):
            return (0.0, 1.0)
        t, _ = ticker.nice_ticks(0, hi, 5)
        return (0.0, float(t[-1]) if len(t) and t[-1] >= hi else hi * 1.05)

    def _geom(self, R):
        x0, y0, x1, y1 = Axes._box_px(self, R)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rad = min(x1 - x0, y1 - y0) / 2
        return cx, cy, rad

    def _polar_xy(self, R, theta, r):
        cx, cy, rad = self._geom(R)
        lo, hi = self.get_ylim()
        rr = (np.asarray(r, np.float64) - lo) / ((hi - lo) or 1.0) * rad
        ang = self._theta_offset + self._theta_dir * np.asarray(theta, np.float64)
        return cx + rr * np.cos(ang), cy - rr * np.sin(ang)

    def pcolormesh(self, T, Rr, C, norm=None, cmap=None, shading='auto', **kw):
        T, Rr, C = (np.asarray(v, np.float64) for v in (T, Rr, C))
        self._update_datalim(None, Rr)
        return self._add('pmesh', 0, T=T, Rr=Rr, C=C, norm=norm or mcolors.Normalize(), cmap=cmap or 'inferno')

    def draw(self, R):
        cv = R.canvas
        cx, cy, rad = self._geom(R)
        circle = np.linspace(0, 2 * np.pi, 361)
        ring = np.column_stack([cx + rad * np.cos(circle), cy - rad * np.sin(circle)])
        box = (cx - rad - 1, cy - rad - 1, cx + rad + 1, cy + rad + 1)
        cv.fill_polys([ring], (1, 1, 1))
        items = self._sorted_with_legend()
        grid_done = False
        for a in items:
            if not grid_done and a['zorder'] >= 1.5:
                self._draw_polar_grid(R)
                grid_done = True
            if a['kind'] == 'legend':
                self._draw_legend(R, (cx - rad, cy - rad, cx + rad, cy + rad))
            else:
                self._draw_polar_artist(R, a, box)
        if not grid_done:
            self._draw_polar_grid(R)
        cv.stroke(ring, self._pt(R, 0.8), (0, 0, 0), closed=True)
        self._draw_polar_labels(R)
        if self._title:
            t = self._title
            above = rad + self._pt(R, 3.5) + 1.9 * self._pt(R, self.xaxis.tick_label_size) + self._pt(R, t['pad'])
            cv.text(cx, cy - above, t['s'], self._pt(R, t['size']),
                    mcolors.to_rgb(t['color']), weight=t['weight'], ha='center')

    def _rticks(self):
        lo, hi = self.get_ylim()
        t, step = ticker.nice_ticks(lo, hi, 9)
        return t[(t > lo + 1e-12) & (t <= hi + 1e-9)], step

    def _draw_polar_grid(self, R):
        cv = R.canvas
        circle = np.linspace(0, 2 * np.pi, 361)
        lo, hi = self.get_ylim()
        major_r, step = self._rticks()
        for which in ('minor', 'major'):
            g = self._grid.get(which)
            if not g:
                continue
            rgb = mcolors.to_rgb(g['color'])
            lw = self._pt(R, g['lw'])
            if which == 'major':
                radii, angles = major_r, self._thetagrids
            else:
                radii = ticker.minor_ticks(np.concatenate([[lo], major_r]), step, lo, hi, self.yaxis.minor_ndivs)                     if self.yaxis.minor else []
                tg = sorted(self._thetagrids)
                tstep = (tg[1] - tg[0]) if len(tg) > 1 else 45.0
                angles = [a for a in np.arange(0, 360, tstep / 4) if not any(abs(a - b) < 1e-6 for b in tg)]                     if self.xaxis.minor else []
            for r in radii:
                px, py = self._polar_xy(R, circle, np.full(circle.shape, r))
                cv.stroke(np.column_stack([px, py]), lw, rgb)
            for deg in angles:
                px, py = self._polar_xy(R, [np.deg2rad(deg)] * 2, [lo, hi])
                cv.stroke(np.column_stack([px, py]), lw, rgb)

    def _draw_polar_labels(self, R):
        cv = R.canvas
        cx, cy, rad = self._geom(R)
        fs = self._pt(R, self.xaxis.tick_label_size)
        lc = mcolors.to_rgb(self.xaxis.tick_label_color)
        for deg in self._thetagrids:
            ang = self._theta_offset + self._theta_dir * np.deg2rad(deg)
            d = rad + self._pt(R, 3.5) + fs * 0.9
            cv.text(cx + d * np.cos(ang), cy - d * np.sin(ang), f'{deg:g}°', fs, lc, ha='center', va='center')
        ticks, step = self._rticks()
        labels, offset = ticker.format_ticks(ticks, step, self.yaxis.sci, self.yaxis.scilimits)
        fsr = self._pt(R, self.yaxis.tick_label_size)
        rc = mcolors.to_rgb(self.yaxis.tick_label_color)
        if offset:
            cv.text(cx - rad * 0.85, cy - rad * 0.85, offset, fsr, (0, 0, 0), ha='center', va='bottom')
        for r, s in zip(ticks, labels):
            px, py = self._polar_xy(R, [np.deg2rad(22.5)], [r])
            cv.text(float(px[0]), float(py[0]), s, fsr, rc, ha='left', va='bottom')

    def _draw_polar_artist(self, R, a, box):
        cv = R.canvas
        k = a['kind']
        cx, cy, rad = self._geom(R)
        clip = (cx - rad, cy - rad, cx + rad, cy + rad)
        if k == 'line':
            px, py = self._polar_xy(R, a['x'], a['y'])
            dashes, on = self._line_style(R, a['ls'], a['lw'])
            rgb = mcolors.to_rgb(a['color'])
            if on:
                cv.stroke(np.column_stack([px, py]), self._pt(R, a['lw']), rgb, a['alpha'], clip, dashes)
            if a['marker']:
                for x_, y_ in zip(px, py):
                    self._draw_marker(R, x_, y_, a['marker'], a['ms'], rgb, a['alpha'], clip)
        elif k == 'poly':
            p = a['poly']
            px, py = self._polar_xy(R, p[:, 0], p[:, 1])
            cv.fill_polys([np.column_stack([px, py])], mcolors.to_rgb(a['color']), a['alpha'], clip)
        elif k == 'vline':
            lo, hi = self.get_ylim()
            r0, r1 = lo + (hi - lo) * a['ymin'], lo + (hi - lo) * a['ymax']
            px, py = self._polar_xy(R, [a['x'], a['x']], [r0, r1])
            dashes, on = self._line_style(R, a['ls'], a['lw'])
            if on:
                cv.stroke(np.column_stack([px, py]), self._pt(R, a['lw']), mcolors.to_rgb(a['color']), a['alpha'],
                          clip, dashes)
        elif k in ('text', 'annot'):
            if k == 'text':
                px, py = self._polar_xy(R, [a['x']], [a['y']])
            else:
                px, py = self._polar_xy(R, [a['xy'][0]], [a['xy'][1]])
                if a['xytext'] is not None and a['textcoords'] == 'offset points':
                    px = px + self._pt(R, a['xytext'][0])
                    py = py - self._pt(R, a['xytext'][1])
            cv.text(float(px[0]), float(py[0]), a['s'], self._pt(R, a['size']), mcolors.to_rgb(a['color']),
                    a['alpha'], a['weight'], a['ha'], a['va'], a['rotation'])
        elif k == 'pmesh':
            self._draw_pmesh(R, a)

    def _draw_pmesh(self, R, a):
        cv = R.canvas
        cx, cy, rad = self._geom(R)
        x0, y0 = int(max(0, np.floor(cx - rad))), int(max(0, np.floor(cy - rad)))
        x1, y1 = int(min(cv.w, np.ceil(cx + rad))), int(min(cv.h, np.ceil(cy + rad)))
        if x1 <= x0 or y1 <= y0:
            return
        T, Rr, C = a['T'], a['Rr'], a['C']
        thetas = T[:, 0] if T.ndim == 2 else T
        radii = Rr[0, :] if Rr.ndim == 2 else Rr
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float64)
        dx, dy = xx + 0.5 - cx, -(yy + 0.5 - cy)
        lo, hi = self.get_ylim()
        r = np.hypot(dx, dy) / rad * (hi - lo) + lo
        ang = (np.arctan2(dy, dx) - self._theta_offset) * self._theta_dir
        ang = np.mod(ang, 2 * np.pi)
        ti = np.clip(np.searchsorted(thetas, ang), 1, len(thetas) - 1)
        ti = np.where(np.abs(ang - thetas[ti - 1]) <= np.abs(thetas[ti] - ang), ti - 1, ti)
        ri = np.clip(np.searchsorted(radii, r), 1, len(radii) - 1)
        ri = np.where(np.abs(r - radii[ri - 1]) <= np.abs(radii[ri] - r), ri - 1, ri)
        vals = a['norm'](C)
        rgba = mcolors.apply_cmap(vals, a['cmap'])[ti, ri]
        inside = (np.hypot(dx, dy) <= rad) & (r >= radii.min()) & (r <= radii.max() + (radii[-1] - radii[-2]) / 2)
        rgba[..., 3] *= inside
        cv.blend_rgba(rgba.astype(np.float32), x0, y0)


class Axes3D(Axes):
    name = '3d'

    def __init__(self, fig, position):
        super().__init__(fig, position)
        self.zaxis = _Axis()
        self._zlim = None
        self.elev, self.azim = 30.0, -60.0
        self._zdatalim = [np.inf, -np.inf]

    def set_zlim(self, bottom=None, top=None, **kw):
        bottom, top = self._lim_arg(bottom, top)
        self._zlim = (float(bottom), float(top))

    def get_zlim(self):
        return self._zlim or self._auto(*self._zdatalim)

    def set_zlabel(self, s, **kw):
        self.zaxis.label = str(s)

    def view_init(self, elev=None, azim=None, **kw):
        if elev is not None:
            self.elev = elev
        if azim is not None:
            self.azim = azim

    def _update3(self, x, y, z):
        self._update_datalim(x, y)
        z = np.asarray(z, np.float64).ravel()
        z = z[np.isfinite(z)]
        if z.size:
            self._zdatalim = [min(self._zdatalim[0], z.min()), max(self._zdatalim[1], z.max())]

    def quiver(self, X, Y, Z, U, V, W, color='black', linewidth=1.5, arrow_length_ratio=0.3, linestyle='-',
               alpha=1.0, normalize=False, length=1.0, **kw):
        P = np.array([X, Y, Z], np.float64).reshape(3, -1).T
        D = np.array([U, V, W], np.float64).reshape(3, -1).T * length
        self._update3(np.r_[P[:, 0], P[:, 0] + D[:, 0]], np.r_[P[:, 1], P[:, 1] + D[:, 1]],
                      np.r_[P[:, 2], P[:, 2] + D[:, 2]])
        return self._add('quiver', kw.get('zorder', 2), P=P, D=D, color=color, lw=kw.get('linewidths', linewidth),
                         ratio=arrow_length_ratio, ls=linestyle, alpha=alpha if alpha is not None else 1.0)

    def text(self, x, y, z, s=None, zdir=None, **kw):
        if s is None:   # 2D call text(x, y, s)
            return super().text(x, y, z, **kw)
        return self._add('text3', kw.get('zorder', 3), p=(float(x), float(y), float(z)), s=str(s), **_text_kw(kw))

    def plot(self, xs, ys, *args, zs=None, **kw):
        if args and not isinstance(args[0], str):
            zs = args[0]
            args = args[1:]
        if zs is None:
            return super().plot(xs, ys, *args, **kw)
        self._update3(xs, ys, zs)
        color = kw.get('color', self._next_color())
        return self._add('line3', kw.get('zorder', 2), P=np.column_stack([np.ravel(xs), np.ravel(ys), np.ravel(zs)]),
                         color=color, lw=kw.get('linewidth', 1.5), ls=kw.get('linestyle', '-'),
                         alpha=kw.get('alpha', 1.0), label=kw.get('label'))

    def _proj(self, R):
        x0, y0, x1, y1 = Axes._box_px(self, R)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        lims = [self.get_xlim(), self.get_ylim(), self.get_zlim()]
        aspect = np.array([4.0, 4.0, 3.0]) / 4.0
        az, el = np.deg2rad(self.azim), np.deg2rad(self.elev)
        right = np.array([-np.sin(az), np.cos(az), 0.0])
        eye = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
        up = np.cross(eye, right)
        scale = min(x1 - x0, y1 - y0) / 2.0 / 1.6

        def f(P):
            P = np.atleast_2d(np.asarray(P, np.float64))
            n = np.empty_like(P)
            for i in range(3):
                lo, hi = lims[i]
                n[:, i] = ((P[:, i] - lo) / ((hi - lo) or 1.0) * 2 - 1) * aspect[i]
            return np.column_stack([cx + scale * (n @ right), cy - scale * (n @ up)]), n @ eye
        return f, lims, eye

    def draw(self, R):
        cv = R.canvas
        f, lims, eye = self._proj(R)
        (xl, xh), (yl, yh), (zl, zh) = lims
        # back panes: the side of each axis facing away from the viewer
        bx = xh if eye[0] < 0 else xl
        by = yh if eye[1] < 0 else yl
        bz = zl
        pane = (0.95, 0.95, 0.95)
        panes = [
            [(bx, yl, zl), (bx, yh, zl), (bx, yh, zh), (bx, yl, zh)],
            [(xl, by, zl), (xh, by, zl), (xh, by, zh), (xl, by, zh)],
            [(xl, yl, bz), (xh, yl, bz), (xh, yh, bz), (xl, yh, bz)],
        ]
        for p in panes:
            q, _ = f(p)
            cv.fill_polys([q], pane, 1.0)
            cv.stroke(q, self._pt(R, 0.6), (0.85, 0.85, 0.85), closed=True)
        gc = mcolors.to_rgb(GRID_DEFAULT)
        gw = self._pt(R, 0.6)
        fs = self._pt(R, 10)
        centre = f([((xl + xh) / 2, (yl + yh) / 2, (zl + zh) / 2)])[0][0]
        minor_rgb = mcolors.to_rgb((self._grid.get('minor') or {}).get('color', 'lightgrey'))
        for i, (lo, hi) in enumerate(lims):
            t, step = ticker.nice_ticks(lo, hi, 8)
            labels, _ = ticker.format_ticks(t, step)
            axis = (self.xaxis, self.yaxis, self.zaxis)[i]
            if axis.minor and 'minor' in self._grid:
                for v in ticker.minor_ticks(t, step, lo, hi, axis.minor_ndivs):
                    if i == 0:
                        lines = [[(v, by, zl), (v, by, zh)], [(v, yl, bz), (v, yh, bz)]]
                    elif i == 1:
                        lines = [[(bx, v, zl), (bx, v, zh)], [(xl, v, bz), (xh, v, bz)]]
                    else:
                        lines = [[(bx, yl, v), (bx, yh, v)], [(xl, by, v), (xh, by, v)]]
                    for ln in lines:
                        q, _ = f(ln)
                        cv.stroke(q, self._pt(R, 0.5), minor_rgb)
            for v, s in zip(t, labels):
                if i == 0:
                    lines = [[(v, by, zl), (v, by, zh)], [(v, yl, bz), (v, yh, bz)]]
                    lab = (v, yl if by == yh else yh, zl)
                elif i == 1:
                    lines = [[(bx, v, zl), (bx, v, zh)], [(xl, v, bz), (xh, v, bz)]]
                    lab = (xl if bx == xh else xh, v, zl)
                else:
                    lines = [[(bx, yl, v), (bx, yh, v)], [(xl, by, v), (xh, by, v)]]
                    lab = (xl if bx == xh else xh, by, v)
                for ln in lines:
                    q, _ = f(ln)
                    cv.stroke(q, gw, gc)
                q, _ = f([lab])
                d = q[0] - centre
                d = d / (np.hypot(*d) or 1.0)
                cv.text(float(q[0, 0] + d[0] * fs * 1.6), float(q[0, 1] + d[1] * fs * 1.6), s, fs, (0.2, 0.2, 0.2),
                        ha='center', va='center')
        for axis, P in ((self.xaxis, ((xl + xh) / 2, yl if by == yh else yh, zl)),
                        (self.yaxis, (xl if bx == xh else xh, (yl + yh) / 2, zl)),
                        (self.zaxis, (xl if bx == xh else xh, by, (zl + zh) / 2))):
            if axis.label:
                q, _ = f([P])
                d = q[0] - centre
                d = d / (np.hypot(*d) or 1.0)
                cv.text(float(q[0, 0] + d[0] * fs * 4.2), float(q[0, 1] + d[1] * fs * 4.2), axis.label,
                        self._pt(R, 10), (0, 0, 0), ha='center', va='center')
        items = sorted(self._artists, key=lambda a: (a['zorder'], a['order']))
        for a in items:
            k = a['kind']
            if k == 'quiver':
                rgb = mcolors.to_rgb(a['color'])
                dashes, on = self._line_style(R, a['ls'], a['lw'])
                for p, d in zip(a['P'], a['D']):
                    q, _ = f([p, p + d])
                    if on:
                        cv.stroke(q, self._pt(R, a['lw']), rgb, a['alpha'], None, dashes)
                    tip = q[1]
                    vec = q[1] - q[0]
                    L = np.hypot(*vec)
                    if L > 0:
                        u = vec / L
                        hl = L * a['ratio']
                        for s in (1, -1):
                            ang = np.deg2rad(30) * s
                            rot = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
                            back = tip - rot @ u * hl
                            cv.stroke([tip, back], self._pt(R, a['lw']), rgb, a['alpha'])
            elif k == 'line3':
                q, _ = f(a['P'])
                dashes, on = self._line_style(R, a['ls'], a['lw'])
                if on:
                    cv.stroke(q, self._pt(R, a['lw']), mcolors.to_rgb(a['color']), a['alpha'], None, dashes)
            elif k == 'text3':
                q, _ = f([a['p']])
                cv.text(float(q[0, 0]), float(q[0, 1]), a['s'], self._pt(R, a['size']), mcolors.to_rgb(a['color']),
                        a['alpha'], a['weight'], a['ha'], a['va'], a['rotation'])
        if self._title:
            t = self._title
            x0, y0, x1, y1 = Axes._box_px(self, R)
            cv.text((x0 + x1) / 2, y0 + self._pt(R, t['size']), t['s'], self._pt(R, t['size']),
                    mcolors.to_rgb(t['color']), weight=t['weight'], ha='center')
        if self._legend is not None:
            self._draw_legend(R, Axes._box_px(self, R))
