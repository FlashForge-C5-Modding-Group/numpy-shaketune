"""matplotlib.pyplot subset backed by the numpy renderer."""
from ._render import read_png
from .figure import Figure

_current_fig = None


def figure(figsize=None, dpi=None, **kw):
    global _current_fig
    _current_fig = Figure(figsize=figsize, dpi=dpi, **kw)
    return _current_fig


def gcf():
    return _current_fig if _current_fig is not None else figure()


def gca():
    return gcf().gca()


def subplots(nrows=1, ncols=1, figsize=None, dpi=None, gridspec_kw=None, subplot_kw=None, squeeze=True, **kw):
    fig = figure(figsize=figsize, dpi=dpi)
    axs = fig.subplots(nrows, ncols, gridspec_kw=gridspec_kw, squeeze=squeeze, subplot_kw=subplot_kw)
    return fig, axs


def table(**kw):
    return gca().table(**kw)


def text(x, y, s, **kw):
    return gca().text(x, y, s, **kw)


def imread(fname, format=None):
    return read_png(str(fname))


def savefig(fname, **kw):
    gcf().savefig(fname, **kw)


def close(fig=None):
    global _current_fig
    if fig is None or fig is _current_fig or fig == 'all':
        _current_fig = None


def switch_backend(name):
    pass


def ioff():
    pass


def show(*a, **k):
    pass
