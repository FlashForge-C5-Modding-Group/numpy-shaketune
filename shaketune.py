# Klipper extra that runs upstream Klippain Shake&Tune with the numpy-only compat layer (README.md).
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
COMPAT = os.path.join(HERE, 'compat')
UPSTREAM = os.path.join(HERE, 'upstream', 'shaketune')
PACKAGE = 'extras.shaketune_upstream'
MIN_MATPLOTLIB = (3, 5)


def _matplotlib_too_old():
    """True when a matplotlib is installed but older than Shake&Tune needs (e.g. 2.2 on Creality K1 firmware)."""
    try:
        from importlib import metadata
        version = metadata.version('matplotlib')
    except Exception:
        return False
    parts = []
    for piece in version.split('.')[:2]:
        digits = ''.join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts) < MIN_MATPLOTLIB


def _use_compat_matplotlib():
    for name in [m for m in sys.modules if m == 'matplotlib' or m.startswith('matplotlib.')]:
        del sys.modules[name]
    path = os.path.join(COMPAT, 'matplotlib')
    spec = importlib.util.spec_from_file_location('matplotlib', os.path.join(path, '__init__.py'),
                                                  submodule_search_locations=[path])
    module = importlib.util.module_from_spec(spec)
    sys.modules['matplotlib'] = module
    spec.loader.exec_module(module)


def _load_upstream():
    if COMPAT not in sys.path:
        sys.path.append(COMPAT)
    if _matplotlib_too_old() and getattr(sys.modules.get('matplotlib'), '__file__', '').find(COMPAT) < 0:
        _use_compat_matplotlib()
    if PACKAGE in sys.modules:
        return sys.modules[PACKAGE]
    init = os.path.join(UPSTREAM, '__init__.py')
    if not os.path.isfile(init):
        raise ImportError('Shake&Tune is not downloaded yet: run the plugin install script (%s)' % UPSTREAM)
    import extras  # noqa: F401  (upstream imports Klipper's shaper_calibrate relative to the extras package)
    spec = importlib.util.spec_from_file_location(PACKAGE, init, submodule_search_locations=[UPSTREAM])
    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(PACKAGE, None)
        raise
    accelerometer = importlib.import_module(PACKAGE + '.helpers.accelerometer')
    _patch_broken_semaphores(accelerometer)
    import _nst_measurements
    _nst_measurements.install(accelerometer)
    return module


def _patch_broken_semaphores(accelerometer):
    """Recording uses multiprocessing.Queue/Value, which hang when POSIX semaphores are broken (K1 firmware)."""
    import _nst_pipequeue
    if not _nst_pipequeue.semaphores_broken():
        return
    accelerometer.Queue = _nst_pipequeue.PipeQueue
    accelerometer.Value = _nst_pipequeue.SharedValue


class _Config:
    """Passes [shaketune] through, with the results folder defaulting to the printer's own config folder."""

    def __init__(self, config):
        self._config = config
        cfg_file = config.get_printer().get_start_args().get('config_file', '')
        self._results = os.path.join(os.path.dirname(os.path.abspath(cfg_file)), 'ShakeTune_results')

    def get(self, option, default=None, *args, **kwargs):
        if option == 'result_folder':
            default = self._results
        return self._config.get(option, default, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._config, name)


def load_config(config):
    return _load_upstream().load_config(_Config(config))
