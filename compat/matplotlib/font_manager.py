"""matplotlib.font_manager subset: FontProperties with named sizes (DejaVu Sans only)."""

SCALINGS = {'xx-small': 0.579, 'x-small': 0.694, 'small': 0.833, 'medium': 1.0, 'large': 1.2,
            'x-large': 1.44, 'xx-large': 1.728, 'larger': 1.2, 'smaller': 0.833}
BASE_SIZE = 10.0


def size_points(size, default=BASE_SIZE):
    if size is None:
        return default
    if isinstance(size, str):
        return BASE_SIZE * SCALINGS.get(size, 1.0)
    return float(size)


class FontProperties:
    def __init__(self, family=None, style=None, variant=None, weight=None, stretch=None, size=None, fname=None):
        self._weight = weight or 'normal'
        self._size = size

    def set_size(self, size):
        self._size = size

    def get_size_in_points(self):
        return size_points(self._size)

    def set_weight(self, weight):
        self._weight = weight

    def get_weight(self):
        return self._weight


def findfont(*args, **kwargs):
    return 'DejaVuSans'
