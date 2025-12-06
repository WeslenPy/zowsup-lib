from ...layers import YowLayer
import logging
from loguru import logger
class YowLoggerLayer(YowLayer):

    def send(self, data):
        ldata = list(data) if type(data) is bytearray else data
        logger.debug(f"tx:\n{ldata}")
        self.toLower(data)

    def receive(self, data):
        ldata = list(data) if type(data) is bytearray else data
        logger.debug(f"rx:\n{ldata}")
        self.toUpper(data)

    def __str__(self):
        return "Logger Layer"