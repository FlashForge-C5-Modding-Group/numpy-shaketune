# Loads Shake&Tune .stdata recordings straight into numpy arrays instead of lists of Python floats (about a third of
# the memory). Shake&Tune only ever reads samples through np.array(), so the results are the same. See README.md.
import json
import warnings

import numpy as np

_KEY = b'"samples":'
_BLOCK = 1 << 20


class _Stream:
    def __init__(self, raw):
        self.raw, self.buf, self.eof = raw, b'', False

    def fill(self):
        if self.eof:
            return False
        more = self.raw.read(_BLOCK)
        if not more:
            self.eof = True
            return False
        self.buf += more
        return True

    def find(self, token, start=0):
        while True:
            i = self.buf.find(token, start)
            if i >= 0 or not self.fill():
                return i


def _numbers(chunk):
    text = chunk.translate(None, b'[]').strip().strip(b',')
    if not text:
        return np.empty(0)
    with warnings.catch_warnings():
        warnings.simplefilter('error')   # a parse problem raises instead of returning a short array
        return np.fromstring(text, dtype=np.float64, sep=',')


def _samples(st):
    """Parse a JSON list of equal-length number lists at the start of st.buf into an (n, k) array."""
    st.find(b']')
    if st.buf.startswith(b'null'):
        st.buf = st.buf[4:]
        return None
    if st.buf.startswith(b'[]'):
        st.buf = st.buf[2:]
        return np.empty((0, 4))
    if not st.buf.startswith(b'[['):
        raise ValueError('unexpected samples format')
    parts, rows = [], 0
    while True:
        end = st.buf.find(b']]')
        last = end >= 0
        cut = end + 2 if last else st.buf.rfind(b'], [') + 1
        if cut > 0:
            chunk, st.buf = st.buf[:cut], st.buf[cut:]
            rows += chunk.count(b'[') - (0 if parts else 1)
            parts.append(_numbers(chunk))
        if last:
            break
        if not st.fill():
            raise ValueError('truncated samples')
    data = np.concatenate(parts) if len(parts) > 1 else parts[0]
    if rows == 0 or data.size % rows:
        raise ValueError('ragged samples')
    return data.reshape(rows, data.size // rows)


def read_stdata(raw):
    """Measurements from a decompressed .stdata stream: one JSON object per line, samples parsed with numpy."""
    st, out = _Stream(raw), []
    while True:
        st.buf = st.buf.lstrip()
        if not st.buf and not st.fill():
            return out
        if not st.buf:
            continue
        key = st.find(_KEY)
        newline = st.buf.find(b'\n')
        if key < 0 or (0 <= newline < key):   # a line without samples: plain JSON
            end = st.find(b'\n')
            line, st.buf = (st.buf, b'') if end < 0 else (st.buf[:end], st.buf[end + 1:])
            if line.strip():
                out.append(json.loads(line.decode('utf-8')))
            continue
        head = st.buf[:key].rstrip().rstrip(b',')
        meas = json.loads((head + b'}').decode('utf-8'))
        st.buf = st.buf[key + len(_KEY):].lstrip()
        meas['samples'] = _samples(st)
        st.buf = st.buf.lstrip()
        if not st.buf.startswith(b'}'):
            raise ValueError('samples is not the last key')
        st.buf = st.buf[1:]
        out.append(meas)


def install(accelerometer):
    manager = accelerometer.MeasurementsManager
    original = manager.load_from_stdata

    def load_from_stdata(self, filename):
        try:
            with open(filename, 'rb') as f:
                with accelerometer.ZstdDecompressor().stream_reader(f) as raw:
                    self.measurements = read_stdata(raw)
            return self.measurements
        except Exception:
            return original(self, filename)

    manager.load_from_stdata = load_from_stdata
