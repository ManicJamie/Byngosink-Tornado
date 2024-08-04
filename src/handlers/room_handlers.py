import shortuuid
import tornado.web

from models import Room
import models

class RoomHandler(tornado.web.RequestHandler):
    async def get(self, room_id):
        uuid = shortuuid.decode(room_id)
        if ((room := await Room.filter(pk=uuid).first()) is None):
            raise tornado.web.HTTPError(404, "Room not found!")
        
        models.ACTIVE_ROOMS[room.short_uuid] = room
        await room.open()

        secret = self.get_cookie("secret")
        if secret is None:
            self.redirect(f"{room_id}/login/")
            return
        
        user = await room.users.all().filter(secret=secret).first()
        if user is None:
            self.redirect(f"{room_id}/login/")
            return
        
        self.render("room.html", room=room, board=await room.board_fill.first())

class BoardHandler(tornado.web.RequestHandler):
    async def get(self, room_id: str):
        uuid = shortuuid.decode(room_id)
        if ((room := await Room.filter(pk=uuid).first()) is None):
            raise tornado.web.HTTPError(404, "Room not found!")
        
        secret = self.get_cookie("secret")
        if (secret is None):
            self.redirect(f"{room_id}/login/")
            return
        
        user = await room.users.all().filter(secret=secret).first()
        if user is None:
            self.redirect(f"{room_id}/login/")
            return
        
        self.render("board.html", room=room, board=await room.board_fill.first(), user=user)

class RoomLoginHandler(tornado.web.RequestHandler):
    async def get(self, room_id):
        uuid = shortuuid.decode(room_id)
        if ((room := await Room.filter(pk=uuid).first()) is None):
            raise tornado.web.HTTPError(404, "Room not found!")
        
        self.render("login.html", room_name=room.name, requires_password=room.requires_password)
    
    async def post(self, room_id):
        uuid = shortuuid.decode(room_id)
        if ((room := await Room.filter(pk=uuid).first()) is None):
            raise tornado.web.HTTPError(404, "Room not found!")
        
        username = self.get_body_argument("username")
        password = self.get_body_argument("password", None)

        try:
            secret = await room.join(username, password)  # type: ignore
        except tornado.web.HTTPError as e:
            if e.status_code != 401:
                raise e
            else:
                self.set_status(401)
                self.finish("Incorrect password")
                return
        
        self.set_cookie("secret", secret, path=f"/rooms/{room_id}", expires_days=7)
        self.redirect(f"/rooms/{room_id}")
