import asyncio
import logging
from pyrtc_volcengine.logger import PYRTC_LOGGER
from app.dialog_session import TerminalDialogSession
from app.config import config


PYRTC_LOGGER.setLevel(logging.INFO)


async def main() -> None:
    session = TerminalDialogSession(config)
    await session.start()

if __name__ == "__main__":
    asyncio.run(main())
