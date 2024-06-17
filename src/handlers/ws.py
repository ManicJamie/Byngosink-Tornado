import logging
from tornado.httputil import HTTPServerRequest
from tornado.web import Application
import tornado.websocket
import pyjson5 as json
import shortuuid

import models

_log = logging.getLogger("byngosink.ws")

class WebsocketHandler(tornado.websocket.WebSocketHandler):
    room: models.Room | None = None
    user: models.User | None = None
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
        _log.info(data)
        match data.pop("verb", "UNKNOWN"):
            case "SYNCED":
                ...
            case _:
                _log.error(f"Unknown verb received; ignoring... {data}")
    
    def on_close(self) -> None:
        if self.room is not None:
            self.room.disconnect(self)
    
    # Send actions
    async def sync(self, **kwargs):
        """Sync data to the client. All data that is yet to be synced will be
        re-sent to the client until they respond with an appropriate SYNCED packet.
        """
        for k, v in kwargs.items():
            try:
                self.to_sync[k].update(v)
            except KeyError:
                continue
        uuid = shortuuid.uuid()
        self.syncs[uuid] = kwargs
        await self.write_message({"verb": "SYNC", "id": uuid} | kwargs)
    
