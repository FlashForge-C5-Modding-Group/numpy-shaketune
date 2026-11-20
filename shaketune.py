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


def _load_upstream():
    if COMPAT not in sys.path:
        sys.path.append(COMPAT)
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
    return module


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
