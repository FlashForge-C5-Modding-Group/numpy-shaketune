"""Stand-in for the GitPython calls Shake&Tune makes (version string only)."""
import os
import shutil
import subprocess

__version__ = '3.1.41+compat'


class GitCommandError(Exception):
    pass


class InvalidGitRepositoryError(Exception):
    pass


def _gitdir(path):
    p = os.path.abspath(str(path))
    while True:
        g = os.path.join(p, '.git')
        if os.path.isdir(g):
            return g
        if os.path.isfile(g):   # worktree / submodule: "gitdir: <path>"
            with open(g) as fh:
                line = fh.read().strip()
            if line.startswith('gitdir:'):
                return os.path.join(p, line.split(':', 1)[1].strip())
        parent = os.path.dirname(p)
        if parent == p:
            raise InvalidGitRepositoryError(str(path))
        p = parent


def _read_sha(gitdir):
    with open(os.path.join(gitdir, 'HEAD')) as fh:
        head = fh.read().strip()
    if not head.startswith('ref:'):
        return head
    ref = head.split(':', 1)[1].strip()
    f = os.path.join(gitdir, ref)
    if os.path.isfile(f):
        with open(f) as fh:
            return fh.read().strip()
    packed = os.path.join(gitdir, 'packed-refs')
    if os.path.isfile(packed):
        with open(packed) as fh:
            for line in fh:
                parts = line.split()
                if len(parts) == 2 and parts[1] == ref:
                    return parts[0]
    raise GitCommandError('cannot resolve HEAD')


class _Cmd:
    def __init__(self, root):
        self._root = root

    def __getattr__(self, name):
        def run(*args):
            exe = shutil.which('git') or shutil.which('git', path='/opt/bin:/usr/local/bin:/usr/bin:/bin')
            if not exe:
                raise GitCommandError('git is not installed')
            r = subprocess.run([exe, '-C', self._root, name.replace('_', '-'), *map(str, args)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise GitCommandError(r.stderr.strip())
            return r.stdout.strip()
        return run


class _Commit:
    def __init__(self, sha):
        self.hexsha = sha


class _Head:
    def __init__(self, gitdir):
        self._gitdir = gitdir

    @property
    def commit(self):
        return _Commit(_read_sha(self._gitdir))


class Repo:
    def __init__(self, path='.', search_parent_directories=False):
        self._gitdir = _gitdir(path)
        self.working_dir = os.path.dirname(self._gitdir) if self._gitdir.endswith('.git') else str(path)
        self.git = _Cmd(self.working_dir)
        self.head = _Head(self._gitdir)
