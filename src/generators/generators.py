from abc import ABC, abstractmethod
import inspect, sys, random
import typing
if typing.TYPE_CHECKING:
    from .Goal import Goal

class GeneratorABC(ABC):
    @staticmethod
    @abstractmethod
    def generate(goals: dict[str, 'Goal'], n: int, seed, **kwargs) -> dict[int, 'Goal']:
        ...  # TODO: adapt generators to be threaded

class BaseGenerator(GeneratorABC):
    @staticmethod
    def generate(goals: dict[str, 'Goal'], n: int, seed, **kwargs) -> dict[int, 'Goal']:
        random.seed(seed)
        return {i: g for i, g in enumerate(random.sample(list(goals.values()), n))}

class FixedGenerator(GeneratorABC):
    @staticmethod
    def generate(goals: dict[str, 'Goal'], n: int, seed, **kwargs) -> dict[int, 'Goal']:
        ...

class SynerGen(GeneratorABC):
    @staticmethod
    def generate(goals: dict[str, 'Goal'], n: int, seed, **kwargs) -> dict[int, 'Goal']:
        ...


_GenType = GeneratorABC
ALL: dict[str, type[_GenType]] = {c[0]: c[1] for c in inspect.getmembers(sys.modules[__name__], inspect.isclass)}
