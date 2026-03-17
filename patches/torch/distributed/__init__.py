"""
torch.distributed stub with auto-submodule import hook.

Intercepts ANY `import torch.distributed.*` and returns a stub module so code
that imports distributed submodules doesn't crash in this single-machine build.
"""
import sys
import types


def is_available() -> bool:
    return False


def is_initialized() -> bool:
    return False


def is_nccl_available() -> bool:
    return False


def is_gloo_available() -> bool:
    return False


def is_mpi_available() -> bool:
    return False


def init_process_group(*args, **kwargs) -> None:
    pass


def get_rank(*args, **kwargs) -> int:
    return 0


def get_world_size(*args, **kwargs) -> int:
    return 1


def barrier(*args, **kwargs) -> None:
    pass


def all_reduce(*args, **kwargs):
    pass


def broadcast(*args, **kwargs):
    pass


def destroy_process_group(*args, **kwargs) -> None:
    pass


def new_group(*args, **kwargs):
    return None


class ReduceOp:
    SUM = 0
    PRODUCT = 1
    MIN = 2
    MAX = 3
    BAND = 4
    BOR = 5
    BXOR = 6


Backend = None
GroupMember = None
group = None


def _make_stub_class(name: str) -> type:
    """Create a stub class that can be used as a base class and has is_available()."""
    return type(name, (object,), {
        '__init__': lambda self, *a, **kw: None,
        'is_available': staticmethod(lambda: False),
        'is_initialized': staticmethod(lambda: False),
    })


class _StubModule(types.ModuleType):
    """
    A module stub that returns stub classes for any attribute access.
    Returning classes (not plain functions) ensures code can:
      - Use attributes as base classes:  class Foo(Joinable): ...
      - Call methods on them:  dist.rpc.is_available()
    """

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.__package__ = name
        self.__path__: list = []  # makes Python treat it as a package
        self.__spec__ = None
        self._stub_cache: dict = {}

    def __getattr__(self, name: str):
        if name.startswith('__'):
            raise AttributeError(name)
        if name not in self.__dict__.get('_stub_cache', {}):
            stub = _make_stub_class(name)
            self.__dict__.setdefault('_stub_cache', {})[name] = stub
        return self.__dict__['_stub_cache'][name]


# Pre-build rpc stub with is_available so `dist.rpc.is_available()` works
rpc = _StubModule('torch.distributed.rpc')
rpc.is_available = lambda: False  # type: ignore[attr-defined]
sys.modules['torch.distributed.rpc'] = rpc

# Pre-build other common submodules
for _name in ('distributed_c10d', 'autograd', 'utils', 'algorithms',
              'fsdp', 'optim', 'elastic', 'checkpoint', 'tensor', '_tensor'):
    _mod = _StubModule(f'torch.distributed.{_name}')
    sys.modules[f'torch.distributed.{_name}'] = _mod

# Pre-build torch.distributed.algorithms.join (used by nn/parallel/distributed.py)
_algorithms = sys.modules.get('torch.distributed.algorithms', _StubModule('torch.distributed.algorithms'))
_join_mod = _StubModule('torch.distributed.algorithms.join')


class Join(_make_stub_class('Join')):
    pass


class Joinable(_make_stub_class('Joinable')):
    pass


class JoinHook(_make_stub_class('JoinHook')):
    pass


_join_mod.Join = Join  # type: ignore[attr-defined]
_join_mod.Joinable = Joinable  # type: ignore[attr-defined]
_join_mod.JoinHook = JoinHook  # type: ignore[attr-defined]
sys.modules['torch.distributed.algorithms.join'] = _join_mod
sys.modules['torch.distributed.algorithms'] = _algorithms


class _DistributedImporter:
    """
    Meta path finder that intercepts any `torch.distributed.*` import
    and returns a _StubModule, preventing ModuleNotFoundError.
    """

    PREFIX = "torch.distributed."

    def find_module(self, fullname: str, path=None):
        if fullname.startswith(self.PREFIX):
            return self
        return None

    def load_module(self, fullname: str):
        if fullname in sys.modules:
            return sys.modules[fullname]
        mod = _StubModule(fullname)
        sys.modules[fullname] = mod
        return mod


# Install the import hook
if not any(isinstance(f, _DistributedImporter) for f in sys.meta_path):
    sys.meta_path.append(_DistributedImporter())
