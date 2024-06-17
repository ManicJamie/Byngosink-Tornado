import functools
from typing import TYPE_CHECKING
from uuid import uuid4
import shortuuid

import tornado

from tortoise.models import Model
from tortoise.fields.base import OnDelete
from tortoise import fields, transactions

from generators import Goal, WrappedGenerator

if TYPE_CHECKING:
    import boards
    import models
    from handlers import WebsocketHandler

generate_secret = functools.partial(shortuuid.random, 16)

ALL_BOARDS: dict[str, type['boards.BoardEngine']] = None  # type:ignore
# set by `boards` to avoid recursive import

class GeneratorInfo(Model):
    uuid = fields.UUIDField(primary_key=True, default=uuid4)
    game = fields.CharField(32)
    name = fields.CharField(32)

class Team(Model):  # TODO: uuid/room composite key?
    uuid = fields.UUIDField(primary_key=True)
    name = fields.CharField(32)
    colour = fields.CharField(16)  # TODO: validate prior, shrink field
    room: fields.ForeignKeyRelation['Room'] = fields.ForeignKeyField("models.Room", "teams")
    
    users: fields.ReverseRelation['User']

class User(Model):
    uuid = fields.UUIDField(primary_key=True)
    name = fields.CharField(16)
    secret = fields.CharField(16, unique=True, default=generate_secret)
    room = fields.ForeignKeyField("models.Room", "users")
    team = fields.ForeignKeyField("models.Team", "users", OnDelete.SET_NULL, null=True)
    
    @property
    def _sockets(self) -> list['WebsocketHandler']:
        if "__sockets" not in vars(self):
            self.__sockets = []
        return self.__sockets
    
    def notify(self, *args):
        for socket in self._sockets:
            socket.write_message({"verb": "NOTIFY"})

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
    translations = fields.JSONField()
    """dict[str, str]"""
    
    teams = fields.ManyToManyField("models.Team", "marks", related_name="goals")
    
    class Meta:  # type:ignore
        unique_together = ("fill", "index")
    
    @classmethod
    @transactions.atomic()
    async def from_goals(cls, fill: 'models.BoardFill', goals: dict[int, Goal]):
        await GoalAlias.bulk_create(GoalAlias(fill=fill, index=i, name=g.name,
                                              translations=g.translations)
                                    for i, g in goals.items())

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
        if "_engine" not in vars(self):
            self._engine = self.board_type(self.meta, self)  # type: ignore
        return self._engine
    
    @property
    def board_type(self) -> type['boards.BoardEngine']:
        """The type of board."""
        return ALL_BOARDS[self.board_name]

    @classmethod
    async def generate(cls, board_name: str, meta: 'boards.BoardMeta', wrapped_gen: WrappedGenerator, seed: str | None):
        async with transactions.in_transaction():
            new = await BoardFill.create(board_name=board_name, meta=meta)
            await GoalAlias.from_goals(new,
                                       wrapped_gen.generator.generate(
                                           wrapped_gen.goals, meta.n, seed))
            return new


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
        return user

    def disconnect(self, socket: 'WebsocketHandler'):
        if ((user := socket.user) is not None):
            try:
                user._sockets.remove(socket)
            except ValueError: pass
            socket.user = None
