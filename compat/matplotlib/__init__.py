"""numpy-only stand-in for the parts of matplotlib Klippain Shake&Tune uses (README.md)."""
from . import axes, colors, figure, font_manager, table, ticker  # noqa: F401
from .colors import _CMAPS

__version__ = '3.9.4+numpycompat'
rcParams = {'font.size': 10.0, 'savefig.dpi': 'figure', 'figure.dpi': 100.0}


class _Colormaps(dict):
    def __getitem__(self, name):
        return _CMAPS[name]


colormaps = _Colormaps(_CMAPS)


def use(backend, force=True):
    pass


def get_backend():
    return 'agg'
