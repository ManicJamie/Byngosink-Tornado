from typing import Any
import tornado

from models import BoardFill

class BoardModule(tornado.web.UIModule):
    """Renders a board type."""
    def render(self, *args: Any, **kwargs: Any) -> bytes:  # type: ignore # Original returns str, but allows bytes override
        b: BoardFill | None = kwargs.get("board", None)
        if not isinstance(b, BoardFill): raise Exception(f"Board passed to BoardModule was not a board! {b.__qualname__}")
        return self.render_string(f"components/boards/{b.engine.TEMPLATE}", board=b, engine=b.engine)
