"""Stand-in for the zstandard calls Shake&Tune makes, using gzip (zlib) streams instead (README.md)."""
import io
import zlib

FLUSH_FRAME = 1
FLUSH_BLOCK = 0
__version__ = '0.23.0+gzipcompat'
_ZSTD_MAGIC = b'\x28\xb5\x2f\xfd'


class ZstdError(Exception):
    pass


class _Writer:
    def __init__(self, f, level):
        self._f = f
        self._c = zlib.compressobj(min(9, max(1, level // 2)), zlib.DEFLATED, 31)

    def write(self, data):
        out = self._c.compress(data)
        if out:
            self._f.write(out)
        return len(data)

    def flush(self, flush_mode=FLUSH_BLOCK):
        if flush_mode == FLUSH_FRAME:
            self._f.write(self._c.flush(zlib.Z_FINISH))
            self._c = zlib.compressobj(6, zlib.DEFLATED, 31)
        else:
            self._f.write(self._c.flush(zlib.Z_SYNC_FLUSH))
        self._f.flush()

    def close(self):
        self.flush(FLUSH_FRAME)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        try:
            self._f.write(self._c.flush(zlib.Z_FINISH))
        except Exception:
            pass
        return False


class ZstdCompressor:
    def __init__(self, level=3, **kw):
        self.level = level

    def stream_writer(self, f, **kw):
        return _Writer(f, self.level)

    def compress(self, data):
        c = zlib.compressobj(min(9, max(1, self.level // 2)), zlib.DEFLATED, 31)
        return c.compress(data) + c.flush()


class _Reader(io.RawIOBase):
    def __init__(self, f):
        self._f = f
        self._d = zlib.decompressobj(47)
        self._buf = b''
        self._eof = False
        head = f.read(4)
        if head == _ZSTD_MAGIC:
            raise ZstdError('this file is real Zstandard data; install the zstandard package to read it')
        self._pending = head

    def readable(self):
        return True

    def _fill(self, n):
        while len(self._buf) < n and not self._eof:
            chunk = self._pending + self._f.read(65536)
            self._pending = b''
            if not chunk:
                self._buf += self._d.flush()
                self._eof = True
                break
            self._buf += self._d.decompress(chunk)
            while self._d.eof and self._d.unused_data:   # concatenated gzip members (one per flush)
                rest = self._d.unused_data
                self._d = zlib.decompressobj(47)
                self._buf += self._d.decompress(rest)

    def readinto(self, b):
        self._fill(len(b))
        n = min(len(b), len(self._buf))
        b[:n] = self._buf[:n]
        self._buf = self._buf[n:]
        return n

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class ZstdDecompressor:
    def __init__(self, **kw):
        pass

    def stream_reader(self, f, **kw):
        return _Reader(f)

    def decompress(self, data, **kw):
        if data[:4] == _ZSTD_MAGIC:
            raise ZstdError('real Zstandard data; install the zstandard package to read it')
        return zlib.decompress(data, 47)
