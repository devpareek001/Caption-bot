from aiohttp import web
from pyrogram import Client

from config import Settings
from DreamXbotz.helpers.logging_setup import configure_logging, get_logger
from DreamXbotz.runtime import state
from DreamXbotz.server import web_server
from DreamXbotz.storage import close_storage, prepare_storage


PLUGIN_PACKAGE = "DreamXbotz"
HOST = "0.0.0.0"
LOGGER = get_logger("DreamXbotz.bootstrap")


def require_runtime_config():
    missing = Settings.missing_required()
    if missing:
        raise RuntimeError(f"Missing required environment variable(s): {', '.join(missing)}")


class DreamXbotzCaptionApp(Client):
    def __init__(self):
        require_runtime_config()
        self.web_runner = None
        self.web_site = None

        super().__init__(
            name=Settings.BOT_USERNAME,
            api_id=Settings.API_ID,
            api_hash=Settings.API_HASH,
            bot_token=Settings.BOT_TOKEN,
            workers=Settings.WORKERS,
            plugins={"root": PLUGIN_PACKAGE},
            sleep_threshold=15,
        )

    async def start(self):
        await prepare_storage()
        await super().start()
        me = await self.get_me()
        self.uptime = Settings.BOT_UPTIME
        state.bot_id = me.id
        state.bot_name = me.first_name or Settings.BOT_USERNAME
        self.force_channel = await self.prepare_force_subscribe()
        await self.start_web_server()
        await self.notify_admins(f"**__{me.first_name} is started.__**")
        LOGGER.info("%s started with %s", me.first_name, Settings.summary())

    async def stop(self, *args):
        if self.web_runner:
            await self.web_runner.cleanup()
        close_storage()
        await super().stop()
        LOGGER.info("DreamXbotz caption bot stopped")

    async def prepare_force_subscribe(self):
        if not Settings.FORCE_SUB:
            return None

        try:
            self.invitelink = await self.export_chat_invite_link(Settings.FORCE_SUB)
            state.force_sub_enabled = True
            return Settings.FORCE_SUB
        except Exception as exc:
            LOGGER.warning("Force-sub channel disabled: %s", exc)
            LOGGER.warning("Make sure the bot is admin in the force-sub channel")
            return None

    async def start_web_server(self):
        self.web_runner = web.AppRunner(await web_server())
        await self.web_runner.setup()
        self.web_site = web.TCPSite(self.web_runner, HOST, Settings.PORT)
        await self.web_site.start()
        state.web_started = True

    async def notify_admins(self, text):
        for admin_id in Settings.ADMINS:
            try:
                await self.send_message(admin_id, text)
            except Exception as exc:
                LOGGER.warning("Could not notify admin %s: %s", admin_id, exc)


def main():
    configure_logging()
    DreamXbotzCaptionApp().run()


if __name__ == "__main__":
    main()
