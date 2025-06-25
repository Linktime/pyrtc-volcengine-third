import asyncio
import logging
from app.dialog_session import LLMDialogSession
from pyrtc_volcengine.logger import PYRTC_LOGGER
from app.config import config


PYRTC_LOGGER.setLevel(logging.INFO)

async def main() -> None:
    session = LLMDialogSession(config)
    await session.start()

if __name__ == "__main__":
    asyncio.run(main())
