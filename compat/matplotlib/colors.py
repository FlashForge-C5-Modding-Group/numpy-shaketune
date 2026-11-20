"""matplotlib.colors subset (numpy only): color parsing, Normalize, LogNorm, the inferno colormap."""
import numpy as np

CYCLE = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
NAMED = {'aliceblue': '#f0f8ff', 'antiquewhite': '#faebd7', 'aqua': '#00ffff', 'aquamarine': '#7fffd4', 'azure': '#f0ffff', 'beige': '#f5f5dc', 'bisque': '#ffe4c4', 'black': '#000000', 'blanchedalmond': '#ffebcd', 'blue': '#0000ff', 'blueviolet': '#8a2be2', 'brown': '#a52a2a', 'burlywood': '#deb887', 'cadetblue': '#5f9ea0', 'chartreuse': '#7fff00', 'chocolate': '#d2691e', 'coral': '#ff7f50', 'cornflowerblue': '#6495ed', 'cornsilk': '#fff8dc', 'crimson': '#dc143c', 'cyan': '#00ffff', 'darkblue': '#00008b', 'darkcyan': '#008b8b', 'darkgoldenrod': '#b8860b', 'darkgray': '#a9a9a9', 'darkgreen': '#006400', 'darkgrey': '#a9a9a9', 'darkkhaki': '#bdb76b', 'darkmagenta': '#8b008b', 'darkolivegreen': '#556b2f', 'darkorange': '#ff8c00', 'darkorchid': '#9932cc', 'darkred': '#8b0000', 'darksalmon': '#e9967a', 'darkseagreen': '#8fbc8f', 'darkslateblue': '#483d8b', 'darkslategray': '#2f4f4f', 'darkslategrey': '#2f4f4f', 'darkturquoise': '#00ced1', 'darkviolet': '#9400d3', 'deeppink': '#ff1493', 'deepskyblue': '#00bfff', 'dimgray': '#696969', 'dimgrey': '#696969', 'dodgerblue': '#1e90ff', 'firebrick': '#b22222', 'floralwhite': '#fffaf0', 'forestgreen': '#228b22', 'fuchsia': '#ff00ff', 'gainsboro': '#dcdcdc', 'ghostwhite': '#f8f8ff', 'gold': '#ffd700', 'goldenrod': '#daa520', 'gray': '#808080', 'green': '#008000', 'greenyellow': '#adff2f', 'grey': '#808080', 'honeydew': '#f0fff0', 'hotpink': '#ff69b4', 'indianred': '#cd5c5c', 'indigo': '#4b0082', 'ivory': '#fffff0', 'khaki': '#f0e68c', 'lavender': '#e6e6fa', 'lavenderblush': '#fff0f5', 'lawngreen': '#7cfc00', 'lemonchiffon': '#fffacd', 'lightblue': '#add8e6', 'lightcoral': '#f08080', 'lightcyan': '#e0ffff', 'lightgoldenrodyellow': '#fafad2', 'lightgray': '#d3d3d3', 'lightgreen': '#90ee90', 'lightgrey': '#d3d3d3', 'lightpink': '#ffb6c1', 'lightsalmon': '#ffa07a', 'lightseagreen': '#20b2aa', 'lightskyblue': '#87cefa', 'lightslategray': '#778899', 'lightslategrey': '#778899', 'lightsteelblue': '#b0c4de', 'lightyellow': '#ffffe0', 'lime': '#00ff00', 'limegreen': '#32cd32', 'linen': '#faf0e6', 'magenta': '#ff00ff', 'maroon': '#800000', 'mediumaquamarine': '#66cdaa', 'mediumblue': '#0000cd', 'mediumorchid': '#ba55d3', 'mediumpurple': '#9370db', 'mediumseagreen': '#3cb371', 'mediumslateblue': '#7b68ee', 'mediumspringgreen': '#00fa9a', 'mediumturquoise': '#48d1cc', 'mediumvioletred': '#c71585', 'midnightblue': '#191970', 'mintcream': '#f5fffa', 'mistyrose': '#ffe4e1', 'moccasin': '#ffe4b5', 'navajowhite': '#ffdead', 'navy': '#000080', 'oldlace': '#fdf5e6', 'olive': '#808000', 'olivedrab': '#6b8e23', 'orange': '#ffa500', 'orangered': '#ff4500', 'orchid': '#da70d6', 'palegoldenrod': '#eee8aa', 'palegreen': '#98fb98', 'paleturquoise': '#afeeee', 'palevioletred': '#db7093', 'papayawhip': '#ffefd5', 'peachpuff': '#ffdab9', 'peru': '#cd853f', 'pink': '#ffc0cb', 'plum': '#dda0dd', 'powderblue': '#b0e0e6', 'purple': '#800080', 'rebeccapurple': '#663399', 'red': '#ff0000', 'rosybrown': '#bc8f8f', 'royalblue': '#4169e1', 'saddlebrown': '#8b4513', 'salmon': '#fa8072', 'sandybrown': '#f4a460', 'seagreen': '#2e8b57', 'seashell': '#fff5ee', 'sienna': '#a0522d', 'silver': '#c0c0c0', 'skyblue': '#87ceeb', 'slateblue': '#6a5acd', 'slategray': '#708090', 'slategrey': '#708090', 'snow': '#fffafa', 'springgreen': '#00ff7f', 'steelblue': '#4682b4', 'tan': '#d2b48c', 'teal': '#008080', 'thistle': '#d8bfd8', 'tomato': '#ff6347', 'turquoise': '#40e0d0', 'violet': '#ee82ee', 'wheat': '#f5deb3', 'white': '#ffffff', 'whitesmoke': '#f5f5f5', 'yellow': '#ffff00', 'yellowgreen': '#9acd32', 'tab:blue': '#1f77b4', 'tab:orange': '#ff7f0e', 'tab:green': '#2ca02c', 'tab:red': '#d62728', 'tab:purple': '#9467bd', 'tab:brown': '#8c564b', 'tab:pink': '#e377c2', 'tab:gray': '#7f7f7f', 'tab:olive': '#bcbd22', 'tab:cyan': '#17becf', 'b': '#0000ff', 'g': '#008000', 'r': '#ff0000', 'c': '#00bfbf', 'm': '#bf00bf', 'y': '#bfbf00', 'k': '#000000', 'w': '#ffffff'}
_INFERNO_HEX = (
    '00000401000501010601010802010a02020c02020e03021004031204031405041706041907051b08051d09061f0a0722'
    '0b07240c08260d08290e092b10092d110a30120a32140b34150b37160b39180c3c190c3e1b0c411c0c431e0c451f0c48'
    '210c4a230c4c240c4f260c51280b53290b552b0b572d0b592f0a5b310a5c320a5e340a5f3609613809623909633b0964'
    '3d09653e0966400a67420a68440a68450a69470b6a490b6a4a0c6b4c0c6b4d0d6c4f0d6c510e6c520e6d540f6d550f6d'
    '57106e59106e5a116e5c126e5d126e5f136e61136e62146e64156e65156e67166e69166e6a176e6c186e6d186e6f196e'
    '71196e721a6e741a6e751b6e771c6d781c6d7a1d6d7c1d6d7d1e6d7f1e6c801f6c82206c84206b85216b87216b88226a'
    '8a226a8c23698d23698f24699025689225689326679526679727669827669a28659b29649d29649f2a63a02a63a22b62'
    'a32c61a52c60a62d60a82e5fa92e5eab2f5ead305dae305cb0315bb1325ab3325ab43359b63458b73557b93556ba3655'
    'bc3754bd3853bf3952c03a51c13a50c33b4fc43c4ec63d4dc73e4cc83f4bca404acb4149cc4248ce4347cf4446d04545'
    'd24644d34743d44842d54a41d74b3fd84c3ed94d3dda4e3cdb503bdd513ade5238df5337e05536e15635e25734e35933'
    'e45a31e55c30e65d2fe75e2ee8602de9612bea632aeb6429eb6628ec6726ed6925ee6a24ef6c23ef6e21f06f20f1711f'
    'f1731df2741cf3761bf37819f47918f57b17f57d15f67e14f68013f78212f78410f8850ff8870ef8890cf98b0bf98c0a'
    'f98e09fa9008fa9207fa9407fb9606fb9706fb9906fb9b06fb9d07fc9f07fca108fca309fca50afca60cfca80dfcaa0f'
    'fcac11fcae12fcb014fcb216fcb418fbb61afbb81dfbba1ffbbc21fbbe23fac026fac228fac42afac62df9c72ff9c932'
    'f9cb35f8cd37f8cf3af7d13df7d340f6d543f6d746f5d949f5db4cf4dd4ff4df53f4e156f3e35af3e55df2e661f2e865'
    'f2ea69f1ec6df1ed71f1ef75f1f179f2f27df2f482f3f586f3f68af4f88ef5f992f6fa96f8fb9af9fc9dfafda1fcffa4'
)


def _lut(hexstr):
    a = np.frombuffer(bytes.fromhex(hexstr), np.uint8).reshape(-1, 3)
    return a.astype(np.float32) / 255.0


_CMAPS = {'inferno': _lut(''.join(_INFERNO_HEX))}


def to_rgba(c, alpha=None):
    """Any matplotlib-style color -> (r, g, b, a) floats."""
    if c is None or (isinstance(c, str) and c.lower() == 'none'):
        return (0.0, 0.0, 0.0, 0.0)
    if isinstance(c, str):
        s = c.strip()
        low = s.lower()
        if low.startswith('c') and low[1:].isdigit() and len(low) == 2:
            s = CYCLE[int(low[1:]) % len(CYCLE)]
        elif low in NAMED:
            s = NAMED[low]
        elif low.replace('.', '', 1).isdigit():          # grey level '0.5'
            v = float(low)
            return (v, v, v, 1.0 if alpha is None else alpha)
        if s.startswith('#'):
            h = s[1:]
            if len(h) in (3, 4):
                h = ''.join(ch * 2 for ch in h)
            r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
            a = int(h[6:8], 16) / 255.0 if len(h) == 8 else 1.0
            return (r, g, b, a if alpha is None else alpha)
        raise ValueError('unknown color %r' % (c,))
    c = tuple(float(v) for v in c)
    if len(c) == 3:
        return c + (1.0 if alpha is None else alpha,)
    return c[:3] + (c[3] if alpha is None else alpha,)


def to_rgb(c):
    return to_rgba(c)[:3]


def to_hex(c):
    r, g, b, _ = to_rgba(c)
    return '#%02x%02x%02x' % tuple(int(round(v * 255)) for v in (r, g, b))


class Normalize:
    def __init__(self, vmin=None, vmax=None, clip=False):
        self.vmin, self.vmax, self.clip = vmin, vmax, clip

    def autoscale_None(self, a):
        a = np.asarray(a, np.float64)
        fin = a[np.isfinite(a)]
        if self.vmin is None:
            self.vmin = float(fin.min()) if fin.size else 0.0
        if self.vmax is None:
            self.vmax = float(fin.max()) if fin.size else 1.0

    def __call__(self, a):
        a = np.asarray(a, np.float64)
        self.autoscale_None(a)
        span = (self.vmax - self.vmin) or 1.0
        return (a - self.vmin) / span


class LogNorm(Normalize):
    def autoscale_None(self, a):
        a = np.asarray(a, np.float64)
        pos = a[np.isfinite(a) & (a > 0)]
        if self.vmin is None:
            self.vmin = float(pos.min()) if pos.size else 1e-10
        if self.vmax is None:
            self.vmax = float(pos.max()) if pos.size else 1.0

    def __call__(self, a):
        a = np.asarray(a, np.float64)
        self.autoscale_None(a)
        lo, hi = np.log10(max(self.vmin, 1e-300)), np.log10(max(self.vmax, 1e-300))
        with np.errstate(divide='ignore', invalid='ignore'):
            out = (np.log10(np.where(a > 0, a, np.nan)) - lo) / ((hi - lo) or 1.0)
        return out


def get_cmap(name):
    return _CMAPS.get(name, _CMAPS['inferno'])


def apply_cmap(values01, cmap='inferno'):
    """values in 0..1 (NaN = transparent) -> rgba float32."""
    lut = get_cmap(cmap) if isinstance(cmap, str) else cmap
    v = np.asarray(values01, np.float64)
    bad = ~np.isfinite(v)
    idx = np.clip((np.where(bad, 0.0, v) * (len(lut) - 1) + 0.5).astype(np.intp), 0, len(lut) - 1)
    rgb = lut[idx]
    a = np.where(bad, 0.0, 1.0)[..., None].astype(np.float32)
    return np.concatenate([rgb, a], axis=-1)
