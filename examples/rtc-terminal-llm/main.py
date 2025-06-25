import asyncio
import logging
from app.dialog_session import LLMDialogSession
from pyrtc_volcengine.logger import PYRTC_LOGGER
from . import config


PYRTC_LOGGER.setLevel(logging.DEBUG)

async def main() -> None:
    session = LLMDialogSession(config.ws_connect_config)
    await session.start()

if __name__ == "__main__":
    asyncio.run(main())
