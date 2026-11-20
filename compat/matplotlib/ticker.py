"""matplotlib.ticker subset: automatic major/minor ticks and scalar labels."""
import math

import numpy as np

STEPS = (1.0, 2.0, 2.5, 5.0, 10.0)


class AutoMinorLocator:
    def __init__(self, n=None):
        self.ndivs = n


class MaxNLocator:
    def __init__(self, nbins=9):
        self.nbins = nbins


def nice_ticks(vmin, vmax, nbins):
    """matplotlib MaxNLocator-like ticks inside [vmin, vmax]."""
    if not (np.isfinite(vmin) and np.isfinite(vmax)):
        return np.array([]), 1.0
    if vmax < vmin:
        vmin, vmax = vmax, vmin
    if vmax - vmin < 1e-300:
        vmin, vmax = vmin - 1, vmax + 1
    nbins = max(1, int(nbins))
    raw = (vmax - vmin) / nbins
    scale = 10 ** math.floor(math.log10(raw))
    step = None
    for s in STEPS:
        if s * scale >= raw * (1 - 1e-9):
            step = s * scale
            break
    if step is None:
        step = 10 * scale
    # matplotlib may need one more step size when rounding pushes the count over nbins + 1
    while True:
        lo = math.floor(vmin / step + 1e-9) * step
        hi = math.ceil(vmax / step - 1e-9) * step
        n = int(round((hi - lo) / step)) + 1
        if n <= nbins + 1 or step > (vmax - vmin) * 10:
            break
        m = step / 10 ** math.floor(math.log10(step))
        nxt = [s for s in STEPS if s > m + 1e-9]
        step = (nxt[0] if nxt else 10.0) * 10 ** math.floor(math.log10(step))
    ticks = lo + step * np.arange(n)
    eps = step * 1e-6
    ticks = ticks[(ticks >= vmin - eps) & (ticks <= vmax + eps)]
    ticks[np.abs(ticks) < step * 1e-9] = 0.0
    return ticks, step


def minor_ticks(major, step, vmin, vmax, ndivs=None):
    if len(major) == 0:
        return np.array([])
    if ndivs is None:
        m = step / 10 ** math.floor(math.log10(step))
        ndivs = 5 if any(abs(m - v) < 1e-6 for v in (1.0, 5.0, 10.0)) else 4
    minor_step = step / ndivs
    lo = math.floor(vmin / minor_step) * minor_step
    t = lo + minor_step * np.arange(int((vmax - lo) / minor_step) + 2)
    t = t[(t >= vmin - 1e-12) & (t <= vmax + 1e-12)]
    k = np.round((t - major[0]) / step * ndivs)
    return t[np.mod(k, ndivs) != 0]


def decimals_for(step):
    for d in range(0, 10):
        if abs(step * 10 ** d - round(step * 10 ** d)) < 1e-6 * max(1.0, step * 10 ** d):
            return d
    return 10


def format_ticks(ticks, step, sci=False, scilimits=(0, 0)):
    """Labels plus offset text ('1e4' style) like ScalarFormatter."""
    if len(ticks) == 0:
        return [], ''
    exp = 0
    amax = float(np.max(np.abs(ticks)))
    if amax > 0:
        oom = math.floor(math.log10(amax))
        lo, hi = scilimits if sci else (-5, 6)
        if sci and lo == 0 and hi == 0:
            exp = oom
        elif oom <= lo or oom >= hi:
            exp = oom
    scaled = ticks / 10 ** exp
    sstep = step / 10 ** exp
    dec = decimals_for(sstep)
    labels = []
    for v in scaled:
        s = f'{v:.{dec}f}'
        if s.startswith('-') and float(s) == 0:
            s = s[1:]
        labels.append(s.replace('-', '−'))
    offset = f'1e{exp}' if exp else ''
    return labels, offset
