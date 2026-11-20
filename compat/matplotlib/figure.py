"""matplotlib.figure subset: Figure, GridSpec, savefig to PNG."""
import numpy as np

from . import colors as mcolors
from ._render import Canvas, write_png_rows
from .axes import Axes, Axes3D, PolarAxes, _text_kw


class SubplotSpec:
    def __init__(self, gs, rows, cols):
        self.gs, self.rows, self.cols = gs, rows, cols

    def get_position(self, fig=None):
        return self.gs._cell_bounds(self.rows, self.cols)


class GridSpec:
    def __init__(self, nrows, ncols, figure=None, left=None, bottom=None, right=None, top=None, wspace=None,
                 hspace=None, width_ratios=None, height_ratios=None):
        self.nrows, self.ncols = nrows, ncols
        self.left = 0.125 if left is None else left
        self.right = 0.9 if right is None else right
        self.bottom = 0.11 if bottom is None else bottom
        self.top = 0.88 if top is None else top
        self.wspace = 0.2 if wspace is None else wspace
        self.hspace = 0.2 if hspace is None else hspace
        self.width_ratios = list(width_ratios) if width_ratios is not None else [1] * ncols
        self.height_ratios = list(height_ratios) if height_ratios is not None else [1] * nrows

    @staticmethod
    def _cells(lo, hi, n, space, ratios):
        tot = hi - lo
        cell = tot / (n + space * (n - 1))
        sep = space * cell
        norm = cell * n / sum(ratios)
        sizes = [r * norm for r in ratios]
        starts, pos = [], lo
        for s in sizes:
            starts.append(pos)
            pos += s + sep
        return starts, sizes

    def _cell_bounds(self, rows, cols):
        xs, ws = self._cells(self.left, self.right, self.ncols, self.wspace, self.width_ratios)
        # rows count from the top
        ys, hs = self._cells(self.bottom, self.top, self.nrows, self.hspace, self.height_ratios[::-1])
        ys, hs = ys[::-1], hs[::-1]
        r0, r1 = rows
        c0, c1 = cols
        x0 = xs[c0]
        x1 = xs[c1 - 1] + ws[c1 - 1]
        y_top = ys[r0] + hs[r0]
        y_bot = ys[r1 - 1]
        return (x0, y_bot, x1 - x0, y_top - y_bot)

    def _norm(self, key, n):
        if isinstance(key, slice):
            start, stop, _ = key.indices(n)
            return (start, stop)
        key = int(key)
        if key < 0:
            key += n
        return (key, key + 1)

    def __getitem__(self, key):
        if isinstance(key, tuple):
            rows, cols = self._norm(key[0], self.nrows), self._norm(key[1], self.ncols)
        else:
            if self.nrows == 1:
                rows, cols = (0, 1), self._norm(key, self.ncols)
            elif self.ncols == 1:
                rows, cols = self._norm(key, self.nrows), (0, 1)
            else:
                k = int(key)
                rows, cols = (k // self.ncols, k // self.ncols + 1), (k % self.ncols, k % self.ncols + 1)
        return SubplotSpec(self, rows, cols)


class FigureText:
    def __init__(self, x, y, s, kw):
        self.x, self.y, self.s, self.kw = x, y, str(s), kw


class _Renderer:
    def __init__(self, canvas, dpi):
        self.canvas, self.dpi, self.w, self.h = canvas, dpi, canvas.w, canvas.h


class Figure:
    def __init__(self, figsize=None, dpi=None, facecolor='white', **kw):
        self.figsize = tuple(figsize) if figsize is not None else (6.4, 4.8)
        self.dpi = dpi or 100
        self.facecolor = facecolor
        self._axes = []
        self._texts = []
        self._counter = 0
        self._current = None

    @property
    def axes(self):
        return list(self._axes)

    def _add_axes(self, ax):
        self._counter += 1
        ax._added = self._counter
        self._axes.append(ax)
        self._current = ax
        return ax

    def add_gridspec(self, nrows=1, ncols=1, **kw):
        return GridSpec(nrows, ncols, figure=self, **kw)

    def _make(self, bounds, projection=None, **kw):
        if projection == 'polar' or kw.get('polar'):
            return PolarAxes(self, bounds)
        if projection == '3d':
            return Axes3D(self, bounds)
        return Axes(self, bounds)

    def add_subplot(self, *args, projection=None, **kw):
        if len(args) == 1 and isinstance(args[0], SubplotSpec):
            spec = args[0]
        else:
            if len(args) == 1:
                n = int(args[0])
                args = (n // 100, (n // 10) % 10, n % 10)
            if len(args) == 0:
                args = (1, 1, 1)
            nrows, ncols, idx = args
            spec = GridSpec(nrows, ncols)[int(idx) - 1]
        ax = self._make(spec.get_position(), projection, **kw)
        ax._subplotspec = spec
        return self._add_axes(ax)

    def add_axes(self, rect, projection=None, anchor=None, **kw):
        ax = self._make(tuple(rect), projection, **kw)
        if anchor:
            ax._anchor = anchor
        return self._add_axes(ax)

    def subplots(self, nrows=1, ncols=1, gridspec_kw=None, squeeze=True, subplot_kw=None, **kw):
        gs = self.add_gridspec(nrows, ncols, **(gridspec_kw or {}))
        axs = np.empty((nrows, ncols), dtype=object)
        for r in range(nrows):
            for c in range(ncols):
                axs[r, c] = self.add_subplot(gs[r, c], **(subplot_kw or {}))
        if squeeze:
            if nrows == 1 and ncols == 1:
                return axs[0, 0]
            if nrows == 1 or ncols == 1:
                return axs.ravel()
        return axs

    def delaxes(self, ax):
        if ax in self._axes:
            self._axes.remove(ax)
        if self._current is ax:
            self._current = max(self._axes, key=lambda a: a._added) if self._axes else None

    def gca(self):
        if self._current is None:
            self.add_subplot(1, 1, 1)
        return self._current

    def sca(self, ax):
        self._current = ax

    def text(self, x, y, s, **kw):
        t = FigureText(float(x), float(y), s, _text_kw(kw))
        self._texts.append(t)
        return t

    def suptitle(self, t, **kw):
        kw.setdefault('ha', 'center')
        kw.setdefault('va', 'top')
        kw.setdefault('fontsize', 12)
        return self.text(0.5, 0.98, t, **kw)

    def set_size_inches(self, w, h=None):
        if h is None:
            w, h = w
        self.figsize = (w, h)

    def tight_layout(self, *a, **k):
        pass

    def savefig(self, fname, dpi=None, **kw):
        dpi = dpi if dpi not in (None, 'figure') else self.dpi
        W, H = int(round(self.figsize[0] * dpi)), int(round(self.figsize[1] * dpi))
        canvas = Canvas(W, H, mcolors.to_rgb(self.facecolor))
        R = _Renderer(canvas, dpi)
        for ax in sorted(self._axes, key=lambda a: (a.zorder, a._added)):
            ax.draw(R)
        for t in self._texts:
            k = t.kw
            canvas.text(t.x * W, (1 - t.y) * H, t.s, k['size'] * dpi / 72.0, mcolors.to_rgb(k['color']), k['alpha'],
                        k['weight'], k['ha'], k['va'], k['rotation'])
        fname = str(fname)
        write_png_rows(fname, canvas.png_bands(), W, H, 3, dpi)

    def clf(self):
        self._axes, self._texts, self._current = [], [], None
