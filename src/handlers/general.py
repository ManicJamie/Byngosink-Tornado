import tornado.web

import boards
import generators
import models


class RootHandler(tornado.web.RequestHandler):
    async def get(self):
        self.render("home.html",
                    gameDict=generators.GEN_NAMES,
                    boardDict=boards.META,
                    roomList=await models.Room.all().order_by("modified").prefetch_related("users"))

class RoomListHandler(tornado.web.RequestHandler):
    async def get(self):
        # TODO: separate room history list here
        self.redirect("/")

    async def post(self):
        room_name: str = self.get_body_argument("room_name")  # type:ignore
        user_name: str = self.get_body_argument("user_name")  # type:ignore
        password = self.get_body_argument("password")
        if password == "": password = None
        board_name: str = self.get_body_argument("board")  # type:ignore
        if board_name not in boards.ALL:
            raise tornado.web.HTTPError(404, f"Could not find board type {board_name}")
        game: str = self.get_body_argument("game")  # type:ignore
        generator: str = self.get_body_argument("generator")  # type:ignore
        try:
            final_gen = generators.WRAPPED_GENS[game][generator]
        except KeyError:
            raise tornado.web.HTTPError(404, f"Could not find generator {game}: {generator}")
        seed = self.get_body_argument("seed")
        if seed == "": seed = None
        
        meta_fields = boards.META[board_name]
        meta = boards.ALL[board_name].meta_type()
        for f in meta_fields:
            meta[f] = self.get_body_argument(f)
        
        # TODO: in transaction?
        r = await models.Room.create(name=room_name, password=password,
                                     board_fill=await models.BoardFill.generate(board_name, meta, final_gen, seed))
        
        user_secret = await r.join(user_name, password)
        self.set_cookie("secret", user_secret, path=f"/rooms/{r.short_uuid}", expires_days=7)
        self.redirect(f"/rooms/{r.short_uuid}")
