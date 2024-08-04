import functools
import logging
import operator
import cachetools
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4
import shortuuid

import tornado

from tortoise.models import Model
from tortoise.fields.base import OnDelete
from tortoise import fields, transactions
from tortoise.validators import RegexValidator
from tortoise.expressions import Q

from generators import Goal, WrappedGenerator

if TYPE_CHECKING:
    import boards
    import models
    from handlers import WebsocketHandler

generate_secret = functools.partial(shortuuid.random, 16)

_log = logging.getLogger("byngosink.models")
_log.setLevel(logging.DEBUG)

ALL_BOARDS: dict[str, type['boards.BoardEngine']] = None  # type:ignore
# set by `boards` to avoid recursive import

class GeneratorInfo(Model):
    uuid = fields.UUIDField(primary_key=True, default=uuid4)
    game = fields.CharField(32)
    name = fields.CharField(32)

class Team(Model):  # TODO: uuid/room composite key?
    """
    :uuid:
    :name: Max. 16
    :colour: Max. 7 (hex colour code)
    :room:
    :users: Members of this team
    """
    uuid = fields.UUIDField(primary_key=True)
    name = fields.CharField(16)
    colour = fields.CharField(7, validators=[RegexValidator(r"^#[0-9A-F]{6}$", 0)])
    room: fields.ForeignKeyRelation['Room'] = fields.ForeignKeyField(
        "models.Room", "teams")
    
    goals: fields.ManyToManyRelation['GoalAlias']
    
    users: fields.ReverseRelation['User']
    
    async def get_marks(self) -> list[int]:
        return [g["index"] for g in await self.goals.all().values("index")]
    
    @property
    async def __json__(self) -> dict[str, dict]:
        return {str(self.uuid): {"name": self.name,
                                 "colour": self.colour,
                                 "users": [{"id": u.uuid, "name": u.name}
                                           for u in await self.users.all()]}}


SOCKETS: dict[UUID, list['WebsocketHandler']] = {}
USERS: dict['WebsocketHandler', UUID] = {}  # TODO: doubly linked teardown here to let GC work

class User(Model):
    uuid = fields.UUIDField(primary_key=True)
    name = fields.CharField(16)
    secret = fields.CharField(16, unique=True, default=generate_secret)
    room: fields.ForeignKeyRelation['Room'] = fields.ForeignKeyField(
        "models.Room", "users")
    team: fields.ForeignKeyRelation['Team'] | None = fields.ForeignKeyField(
        "models.Team", "users", OnDelete.SET_NULL, null=True)
    
    @property
    def _sockets(self):
        if self.uuid not in SOCKETS:
            SOCKETS[self.uuid] = []
        return SOCKETS[self.uuid]
    
    async def sync(self, *,
                   teams: list[Team] | None = None,
                   goals: dict[int, dict[str, Any]] | None = None,
                   marks: dict[str, list[int]] | None = None):
        kwargs = {}
        if teams is not None:
            kwargs["teams"] = {}
            for t in teams:
                kwargs["teams"] |= await t.__json__
        if goals is not None:
            kwargs["goals"] = goals
        if marks is not None:
            kwargs["marks"] = marks
        for socket in self._sockets:
            socket.sync(**kwargs)

class GoalAlias(Model):
    """Goal data required for frontend display (generation metadata removed)
    
    UNIQUE (board, index), backing PKEY auto-generated as Tortoise cannot support composite PKEY.
    
    :fill: BoardFill this goal belongs to
    :index:
    :name:
    :translations: `dict[str, str]` where key is a country code & value is alternate text.
    """
    fill = fields.ForeignKeyField("models.BoardFill", "goals")
    index = fields.SmallIntField()
    
    name = fields.TextField()
    translations: dict[str, str] = fields.JSONField()  # type: ignore
    """dict[str, str]"""
    
    teams = fields.ManyToManyField("models.Team", "marks", related_name="goals")
    
    class Meta:  # type:ignore
        unique_together = ("fill", "index")
    
    @property
    async def __json__(self):
        return {self.index: {"name": self.name,
                             "translations": self.translations}}
    
    @classmethod
    @transactions.atomic()
    async def from_goals(cls, fill: 'models.BoardFill', goals: dict[int, Goal]):
        await GoalAlias.bulk_create(GoalAlias(fill=fill, index=i, name=g.name,
                                              translations=g.translations)
                                    for i, g in goals.items())


ENGINES: 'dict[UUID, boards.BoardEngine]' = {}

class BoardFill(Model):
    """Persistent data from a filled board."""
    uuid = fields.UUIDField(primary_key=True)
    board_name = fields.CharField(32)
    """Name of the board type used."""
    meta = fields.JSONField()
    """Metadata related to the board used."""
    
    goals: fields.ReverseRelation['GoalAlias']
    room: fields.BackwardOneToOneRelation['Room']
    
    @property
    def engine(self) -> 'boards.BoardEngine':
        eng = ENGINES.get(self.uuid, None)
        if eng is None:
            ENGINES[self.uuid] = eng = self.board_type(self)
        return eng
    
    @property
    def board_type(self) -> type['boards.BoardEngine']:
        """The type of board."""
        return ALL_BOARDS[self.board_name]
    
    async def all_goals(self) -> dict[str, dict[str, str | dict[str, str]]]:
        await self.fetch_related("goals")
        return {str(o.index): {"name": o.name,
                               "translations": o.translations}
                for o in await self.goals.all()}
    
    async def goal_json(self, *indices) -> dict[int, dict[str, str | dict[str, str]]]:
        await self.fetch_related("goals")
        index_q: Q = functools.reduce(operator.__or__, [Q(index=i) for i in indices])
        return {o.index: {"name": o.name,
                          "translations": o.translations}
                for o in await self.goals.filter(index_q)}

    @classmethod
    async def generate(cls, board_name: str, meta: 'boards.BoardMeta', wrapped_gen: WrappedGenerator, seed: str | None):
        async with transactions.in_transaction():
            new = await BoardFill.create(board_name=board_name, meta=meta)
            await GoalAlias.from_goals(new,
                                       wrapped_gen.generator.generate(
                                           wrapped_gen.goals, meta.n, seed))
            return new


ACTIVE_ROOMS: cachetools.TTLCache[str, 'Room'] = cachetools.TTLCache(500, 86400)

class Room(Model):
    """Room database model.
    
    :name: Room name.
    :password: Optional password to check against.
    :board_fill: data for a filled board (goals, type & metadata)
    """
    uuid = fields.UUIDField(primary_key=True, default=uuid4)
    name = fields.CharField(32)
    password = fields.CharField(32, null=True)
    board_fill: fields.OneToOneRelation['BoardFill'] = fields.OneToOneField("models.BoardFill", "room")
    modified = fields.DatetimeField(auto_now=True)
    
    teams: fields.ReverseRelation['Team']
    users: fields.ReverseRelation['User']
    
    @property
    def short_uuid(self): return shortuuid.encode(self.uuid)
    
    @property
    def requires_password(self): return self.password is not None
    
    async def open(self):
        await self.fetch_related("teams", "users", "board_fill")
        await self.board_fill.fetch_related("goals")
        ACTIVE_ROOMS[self.short_uuid] = self
    
    async def join(self, username: str, password: str | None):
        if self.password is not None:
            if self.password != password:
                raise tornado.web.HTTPError(401, "Incorrect password")
        
        user = await User.create(name=username, room=self)
        return user.secret
    
    async def leave(self, user: User):  # TODO: should duplicate sessions be allowed to live?
        for socket in user._sockets:
            socket.close()
        await user.delete()
    
    async def connect(self, socket: 'WebsocketHandler'):
        user = await self.users.filter(secret=socket.secret).first()
        if user is None:
            raise tornado.web.HTTPError(401, "Secret not recognised; login required.")
        user._sockets.append(socket)
        socket.sync(**(await self.join_data()))
        return user

    def disconnect(self, socket: 'WebsocketHandler'):
        if ((user := socket.user) is not None):
            try:
                user._sockets.remove(socket)
            except ValueError: pass
        # This socket will close, no socket cleanup required
    
    async def join_data(self):
        out = {}
        teams = await Team.filter(room=self.uuid)
        if len(teams) > 0:
            out["teams"] = functools.reduce(operator.or_, [{}] + [(await t.__json__) for t in teams])
        out["goals"] = (await (await self.board_fill).engine.get_min_view())["goals"]
        return out
    
    async def sync_teams(self):
        await tornado.gen.multi([user.sync(teams=await self.teams.all())
                                 for user in await self.users.all()])
    
    async def sync_goals(self, *indices: int):
        await tornado.gen.multi([user.sync(goals=await (await self.board_fill).goal_json(indices))
                                 for user in await self.users.all()])
    
    async def sync_marks(self, team: Team, all: bool = False):
        if all:
            targets = await self.users.all()
        else:
            targets = await team.users.all()
        await tornado.gen.multi([user.sync(marks={str(team.uuid): (await team.get_marks())})
                                 for user in targets])
