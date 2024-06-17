from typing import Any

import models

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
    """The engine used at runtime to assess views, marking & metadata."""
    TEMPLATE: str = "basic.html"
    name: str = "Non-Lockout"
    meta: BasicBoardMeta
    meta_type: type[BoardMeta] = BasicBoardMeta
    fill: 'models.BoardFill'
    
    def __init__(self, meta: BasicBoardMeta, fill: 'models.BoardFill') -> None:
        self.meta = self.meta_type(meta)  # type: ignore
        self.fill = fill
    
    async def get_full_view_meta(self):
        return {}
    
    async def get_full_view(self) -> dict[str, Any]:
        return {"goals": ..., "marks": ...}
    
    async def get_team_view_meta(self) -> dict:
        return await self.get_full_view_meta()
    
    async def get_team_view(self, team: 'models.Team') -> dict[str, Any]:
        # TODO: passing Team or Team.id here?
        return await self.get_full_view() | await self.get_team_view_meta()
    
    async def mark(self, team: 'models.Team', index: int) -> bool:
        goal = await self.fill.goals.filter(index=index).first()
        if goal is None:
            return False
        if team in goal.teams:
            return False
        return True
    
    async def unmark(self, team: 'models.Team', index: int):
        goal = await self.fill.goals.filter(index=index).first()
        if goal is None:
            return False
        if team in goal.teams:
            return False
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
