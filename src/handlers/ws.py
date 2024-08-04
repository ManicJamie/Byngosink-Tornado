import logging
import orjson
from tornado.httputil import HTTPServerRequest
from tornado.web import Application
import tornado.websocket
import pyjson5 as json
import shortuuid

import models

_log = logging.getLogger("byngosink.ws")
_log.setLevel(logging.DEBUG)

class WebsocketHandler(tornado.websocket.WebSocketHandler):
    room: models.Room = None  # type: ignore
    user: models.User = None  # type: ignore
    syncs: dict[str, dict]
    to_sync: dict[str, dict]
    
    def __init__(self, application: Application, request: HTTPServerRequest, **kwargs) -> None:
        super().__init__(application, request, **kwargs)
        self.syncs = {}
        self.to_sync = {
            "marks": {},
            "goals": {},
            "teams": {},
            "chat": {}
        }
    
    @property
    def _current_sync(self):
        return {k: v for k, v in self.to_sync.items() if len(v) > 0}
    
    async def open(self, *args: str, **kwargs: str) -> None:
        room_id = shortuuid.decode(args[0])
        if ((room := await models.Room.get_or_none(uuid=room_id)) is None):
            return self.close(404, "Room not found!")
        self.room = room
        
        if (cookie := self.cookies.get("secret", None)) is None:
            return self.close(401, "No secret provided!")
        self.secret = cookie.value
        
        self.user = await self.room.connect(self)
    
    async def on_message(self, message: str | bytes) -> None:
        if isinstance(message, bytes): message = message.decode()
        data: dict = json.loads(str(message))
        _log.debug(data)
        v = data.pop("verb", "UNKNOWN")
        try:
            match v:
                case "SYNCED":
                    self.synced(data["id"])
                case "CREATE_TEAM":
                    t = await models.Team.create(name=data["name"],
                                                 colour=data["colour"],
                                                 room=self.room)
                    await self.room.sync_teams()
                case "JOIN_TEAM":
                    t = await self.room.teams.filter(uuid=data["uuid"]).first()
                    if t is None:
                        raise Exception(f"Team {data['uuid']} not found!")
                    await models.User.filter(uuid=self.user.uuid).update(team=t)
                    await self.room.sync_teams()
                case "MARK":
                    t = self.user.team
                    if t is None:
                        raise Exception("You need to be in a team to mark goals!")
                    t = await t
                    
                    if data["mark"] is True:
                        result = await (await self.room.board_fill).engine.mark(t, data["index"])
                    else:
                        result = await (await self.room.board_fill).engine.unmark(t, data["index"])
                    
                    if result:
                        await self.room.sync_marks(t, (await self.room.board_fill).board_type.public)
                case _:
                    _log.error(f"Unknown verb received; ignoring: {v}: {data}")
        except KeyError as e:
            _log.error(f"Bad request: {e}")
            self.write_message({"verb": "ERROR", "message": f"Message missing required data {e.args[0]}"})
        except Exception as e:
            _log.error(f"Bad request: {e}", exc_info=True)
            self.write_message({"verb": "ERROR", "message": e.args[0]})
    
    def on_close(self) -> None:
        if self.room is not None:
            self.room.disconnect(self)
    
    def sync(self, **kwargs):
        """Sync data to the client. All data that is yet to be synced will be
        re-sent to the client until they respond with an appropriate SYNCED packet.
        
        Send-and-forget - see SYNCED packets.
        """
        for k, v in kwargs.items():
            try:
                self.to_sync[k].update(v)
            except KeyError:
                continue
        uuid = shortuuid.uuid()
        self.syncs[uuid] = kwargs
        out = {"verb": "SYNC", "id": uuid} | self._current_sync
        _log.debug(out)
        self.write_message(orjson.dumps(out))
    
    def synced(self, id):
        sync = self.syncs.pop(id, {})
        for k, v in sync.items():
            for k2 in v:
                self.to_sync[k].pop(k2, None)
