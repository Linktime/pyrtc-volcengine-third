import logging


PYRTC_LOGGER = logging.getLogger("pyrtc-volcengine")
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter('%(asctime)s - pyrtc-volcengine - %(levelname)s: %(message)s'))
PYRTC_LOGGER.addHandler(_handler)
PYRTC_LOGGER.setLevel(logging.ERROR)
