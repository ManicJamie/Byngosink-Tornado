import asyncio, os, ssl
import logging

import tornado
import tornado.websocket
import tornado.template

from tortoise import Tortoise

from handlers import HANDLERS, modules

_log = logging.getLogger("byngosink")
_log.setLevel(logging.INFO)

root = os.path.dirname(__file__)

def get_chains():
    FULLCHAIN = os.environ.get("FULLCHAIN_PATH", "")
    PRIVKEY = os.environ.get("PRIVKEY_PATH", "")
    PASSWORD = os.environ.get("PASSWORD", None)
    
    return (FULLCHAIN, PRIVKEY, PASSWORD)

async def get_ssl_context() -> ssl.SSLContext | None:
    FULLCHAIN, PRIVKEY, PASSWORD = get_chains()
    
    if os.path.exists(FULLCHAIN) and os.path.exists(PRIVKEY):  # Do SSL if the certificates exist, otherwise warn
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(FULLCHAIN, PRIVKEY, PASSWORD)
        return ssl_context
    else:
        _log.warning("Certs not found: SSL not enabled!")
        return None

async def ensure_ssl(ctx: ssl.SSLContext | None):
    if ctx is None:
        return
    while True:
        await asyncio.sleep(10)  # 2 weeks == 604800 * 2, low for debug purposes
        ctx.load_cert_chain(*get_chains())

async def main():
    application = tornado.web.Application(
        HANDLERS,
        template_path=os.path.join(root, "templates"),
        static_path=os.path.join(root, "static"),
        ui_modules=modules.ALL,
        # DEBUG
        debug=True,
        autoreload=False
    )
    SSL_CONTEXT = await get_ssl_context()
    asyncio.ensure_future(ensure_ssl(SSL_CONTEXT))  # Listens for ssl
    try:
        await Tortoise.init(db_url="sqlite://db.sqlite3", modules={"models": ["models"]})
        await Tortoise.generate_schemas()
        application.listen(80 if SSL_CONTEXT is None else 443, ssl_options=SSL_CONTEXT)
        await asyncio.Future()  # Pass off control forever
    finally:
        await Tortoise.close_connections()

if __name__ == "__main__":
    try:
        import dotenv
        dotenv.load_dotenv()
    except ImportError: pass
    asyncio.run(main())
