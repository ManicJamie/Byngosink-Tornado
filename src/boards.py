from typing import Any
import logging

import models

_log = logging.getLogger("byngosink.boards")
_log.setLevel(logging.DEBUG)

class BoardMeta(dict):
    """Board metadata base class."""
    @property
    def n(self) -> int:
        """Number of goals to be generated (based on other metadata)"""
        raise NotImplementedError()

class BasicBoardMeta(BoardMeta):
    width: int
    height: int
    
    @property
    def n(self):
        return int(self["width"]) * int(self["height"])  # TODO: this is temp,
        # handler should typecheck

class BoardEngine():
    """The engine used at runtime to assess views, marking & metadata.
    
    Meta is data about the board, Live_meta is extra data generated from the fill."""
    TEMPLATE: str = "basic.html"
    name: str = "Non-Lockout"
    meta_type: type[BoardMeta] = BasicBoardMeta
    public: bool = True
    """Whether marks are visible to other teams."""
    live_meta: dict
    fill: 'models.BoardFill'
    
    def __init__(self, fill: 'models.BoardFill') -> None:
        self.fill = fill
        self.live_meta = {}
    
    def __del__(self):
        _log.debug("Deleted board engine!")
    
    async def get_min_view(self):
        return await self.get_full_view()  # Non-hidden
    
    async def get_live_meta_full(self):
        return {}
    
    async def get_live_meta_team(self, team: 'models.Team') -> dict:
        return {}
    
    async def get_full_view(self, reveal: bool = False) -> dict[str, Any]:
        return {"goals": await self.fill.all_goals(),
                "marks": {}}
    
    async def get_team_view(self, team: 'models.Team') -> dict[str, Any]:
        return await self.get_full_view()
    
    async def visible(self, team: 'models.Team | None', reveal=False):
        """Dict [index, SeeAllMarks]"""
        return {i: True for i in range(len(self.fill.goals))}
    
    async def mark(self, team: 'models.Team', index: int) -> bool:
        goal = await self.fill.goals.filter(index=index).first()
        if goal is None: return False
        await goal.fetch_related("teams")
        if team in goal.teams:
            return False
        await goal.teams.add(team)
        return True
    
    async def unmark(self, team: 'models.Team', index: int):
        goal = await self.fill.goals.filter(index=index).first()
        if goal is None:
            return False
        if team not in await goal.teams:
            return False
        await goal.teams.remove(team)
        return True

class NonLockout(BoardEngine):
    name = "Non-Lockout"

class Lockout(BoardEngine):
    name = "Lockout"
    
    async def mark(self, team: 'models.Team', index: int) -> bool:
        ...

class Exploration(BoardEngine):
    name = "Exploration"
    
    def visible_goals(self, team: 'models.Team'):
        ...
    
    async def mark(self, team: 'models.Team', index: int) -> bool:
        ...


ALL: dict[str, type[BoardEngine]] = {b.name: b for b in [
    BoardEngine
]}

META: dict[str, list[str]] = {  # TODO: add typehints and limits to output
    "Non-Lockout": ["width", "height"]
}

models.ALL_BOARDS = ALL  # Avoid recursive import
