# Semaphore-free stand-ins for multiprocessing.Queue and Value, for systems whose POSIX semaphores are broken
# (Creality K1 firmware). One producer and one consumer, shared through fork. See README.md.
import mmap
import os
import pickle
import struct
import threading

_COUNTER = struct.Struct('q')


class PipeQueue:
    def __init__(self, *args, **kwargs):
        self._r, self._w = os.pipe()
        # puts are counted by the producer and gets by the consumer, each in its own slot
        self._counts = mmap.mmap(-1, 2 * _COUNTER.size)

    def _count(self, slot):
        return _COUNTER.unpack_from(self._counts, slot * _COUNTER.size)[0]

    def _bump(self, slot):
        _COUNTER.pack_into(self._counts, slot * _COUNTER.size, self._count(slot) + 1)

    def put(self, obj, block=True, timeout=None):
        data = pickle.dumps(obj, pickle.HIGHEST_PROTOCOL)
        view = memoryview(struct.pack('I', len(data)) + data)
        self._bump(0)
        while view:
            view = view[os.write(self._w, view):]

    def _read(self, size):
        chunks = []
        while size:
            chunk = os.read(self._r, min(size, 1 << 20))
            if not chunk:
                raise EOFError('queue closed')
            chunks.append(chunk)
            size -= len(chunk)
        return b''.join(chunks)

    def get(self, block=True, timeout=None):
        (size,) = struct.unpack('I', self._read(4))
        obj = pickle.loads(self._read(size))
        self._bump(1)
        return obj

    def qsize(self):
        return self._count(0) - self._count(1)

    def empty(self):
        return self.qsize() <= 0


class SharedValue:
    def __init__(self, typecode, value=0, *args, **kwargs):
        self._mem = mmap.mmap(-1, 8)
        self._lock = threading.Lock()
        self.value = value

    @property
    def value(self):
        return _COUNTER.unpack_from(self._mem, 0)[0]

    @value.setter
    def value(self, value):
        _COUNTER.pack_into(self._mem, 0, int(value))

    def get_lock(self):
        return self._lock


def semaphores_broken():
    try:
        import multiprocessing
        lock = multiprocessing.Lock()
        lock.acquire()
        lock.release()
        return False
    except Exception:
        return True
