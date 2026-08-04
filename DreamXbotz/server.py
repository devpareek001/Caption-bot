from aiohttp import web
from config import Settings
from .runtime import state

routes = web.RouteTableDef()

def service_payload():
    return {
        "ok": True,
        "service": Settings.BOT_USERNAME,
        "bot_name": state.bot_name,
        "uptime": state.uptime_seconds,
        "web": state.web_started,
        "force_sub": state.force_sub_enabled,
    }


@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response(service_payload())


@routes.get("/health", allow_head=True)
async def health_check(request):
    return web.json_response({"ok": True})


@routes.get("/metrics", allow_head=True)
async def metrics(request):
    return web.json_response(service_payload())

async def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app["service"] = Settings.BOT_USERNAME
    web_app.add_routes(routes)
    return web_app
