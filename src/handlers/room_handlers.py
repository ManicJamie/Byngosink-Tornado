import shortuuid
import tornado.web

from models import Room

class RoomHandler(tornado.web.RequestHandler):
    async def get(self, room_id):
        uuid = shortuuid.decode(room_id)
        if ((room := await Room.filter(pk=uuid).first()) is None):
            raise tornado.web.HTTPError(404, "Room not found!")

        secret = self.get_cookie("secret")
        if secret is None:
            # TODO: redirect to login page
            raise tornado.web.HTTPError(401, "Not logged in")
        
        user = await room.users.all().filter(secret=secret).first()
        if user is None:
            # TODO: redirect to login page
            raise tornado.web.HTTPError(403, "Secret not recognised")
        
        self.render("room.html", room=room, board=await room.board_fill.first())

class BoardHandler(tornado.web.RequestHandler):
    async def get(self, room_id: str):
        uuid = shortuuid.decode(room_id)
        if ((room := await Room.filter(pk=uuid).first()) is None):
            raise tornado.web.HTTPError(404, "Room not found!")
        
        self.render("board.html", room=room, board=await room.board_fill.first())

class RoomLoginHandler(tornado.web.RequestHandler):
    async def get(self, room_id):
        uuid = shortuuid.decode(room_id)
        if ((room := await Room.filter(pk=uuid).first()) is None):
            raise tornado.web.HTTPError(404, "Room not found!")
        
        print(room)
