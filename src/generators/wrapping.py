import logging, os
from enum import IntEnum
from typing import Any
import pyjson5 as json
from . import generators
from .Goal import Goal

class LanguageLevel(IntEnum):
    PRESENT = 0
    """Translations exist, but may not have full coverage or be up to date."""
    FULL = 1
    """Translations are complete."""


class WrappedGenerator():
    """Defines a generator and goals to be passed to it.
    
    WARN: tears down `src` on construction."""
    
    game: str | None  # TODO: direct ref?
    name: str
    generator: type[generators._GenType]
    goals: dict[str, Goal]
    languages: dict[str, LanguageLevel]
    generatorSettings: dict[str, Any]
    
    def __init__(self, src: dict[str, Any], game: str | None = None, name: str | None = None) -> None:
        self.generator = generators.ALL[src.pop("type", None)]
        gList: dict[str, dict] = src.pop("goals")
        self.goals = {}
        for gid, g in gList.items():
            self.goals[gid] = Goal(g, gid)
        # NonRequired
        self.game = game
        self.name = name if name is not None else "Custom"
        self.languages = src.pop("languages", {})
        self.generatorSettings = src  # Remaining settings


def decode_wrappers(src: str, game: str) -> dict[str, WrappedGenerator]:
    data: dict[str, dict] = json.loads(src)
    out = {}
    for name, gen in data.items():
        try:
            out[name] = WrappedGenerator(gen, name=name, game=game)
        except Exception:
            logging.error(f"Failed to construct gen {name}", exc_info=True)
    return out


WRAPPED_GENS: dict[str, dict[str, WrappedGenerator]] = {}
_jsons = os.listdir(os.path.join(os.path.dirname(__file__), "jsons"))
for j in _jsons:
    game, _ = os.path.splitext(j)
    with open(os.path.join(os.path.dirname(__file__), "jsons", j), encoding="utf-8") as f:
        gens = decode_wrappers(f.read(), game)
        WRAPPED_GENS[game] = {name: gen for name, gen in gens.items()}

GEN_NAMES: dict[str, list[str]] = {game: list(gen.keys()) for game, gen in WRAPPED_GENS.items()}
