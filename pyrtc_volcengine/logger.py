import logging


PYRTC_LOGGER = logging.getLogger("pyrtc-volcengine")
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter('[%(levelname)s]%(asctime)s - pyrtc-volcengine: %(message)s'))
PYRTC_LOGGER.addHandler(_handler)
PYRTC_LOGGER.setLevel(logging.ERROR)
