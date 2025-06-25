import asyncio
import logging
from pyrtc_volcengine.logger import PYRTC_LOGGER
from app.dialog_session import TerminalDialogSession
from . import config


PYRTC_LOGGER.setLevel(logging.DEBUG)


async def main() -> None:
    session = TerminalDialogSession(config.ws_connect_config)
    await session.start()

if __name__ == "__main__":
    asyncio.run(main())
