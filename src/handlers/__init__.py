from tornado.routing import _RuleList

from .general import RootHandler, RoomListHandler
from .room_handlers import BoardHandler, RoomHandler, RoomLoginHandler
from .ws import WebsocketHandler

HANDLERS: _RuleList = \
    [
        (r"/", RootHandler),
        (r"/rooms/?", RoomListHandler),
        (r"/rooms/([^/]*)/?", RoomHandler),
        (r"/rooms/([^/]*)/login/?", RoomLoginHandler),
        (r"/rooms/([^/]*)/board/?", BoardHandler),
        (r"/rooms/([^/]*)/ws/?", WebsocketHandler)
    ]
