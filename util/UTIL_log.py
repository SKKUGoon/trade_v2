from util.UTIL_notifier import *

import datetime
import json
import logging
import logging.handlers
import os
import pprint
from queue import Queue


class Logger:
    def __init__(self, path, name="", queue=None):
        self.propagate = 0
        self.make_log_folder(path)

        if queue is None:
            self.qu = Queue()
        else:
            self.qu = queue
        self.messenger = LineNotifier()
        now = datetime.datetime.now().strftime("%Y%m%d")
        file_path = f"{path}/{now}.txt"

        self.__logger = logging.getLogger(name)
        self.__logger.setLevel(logging.DEBUG)

        format = logging.Formatter('[%(asctime)s][%(levelname)s] >> %(message)s')

        file_handle = logging.FileHandler(file_path)
        file_handle.setFormatter(format)
        self.__logger.addHandler(file_handle)

        stream_handle = logging.StreamHandler()
        stream_handle.setFormatter(format)
        self.__logger.addHandler(stream_handle)

    def make_log_folder(self, path):
        if not os.path.exists(path):
            os.mkdir(path)

    def debug(self, msg, pretty=True):
        if pretty:
            msg = self.make_pretty(msg)
        self.qu.put(msg)
        self.__logger.debug(msg)

    def info(self, msg, pretty=True):
        if pretty:
            msg = self.make_pretty(msg)
        self.qu.put(msg)
        self.__logger.info(msg)

    def warning(self, msg, pretty=True):
        if pretty:
            msg = self.make_pretty(msg)
        self.qu.put(msg)
        self.__logger.warning(msg)

    def error(self, msg, pretty=True):
        if pretty:
            msg = self.make_pretty(msg)
        self.qu.put(msg)
        self.messenger.post_message(msg)
        self.__logger.error(msg)

    def critical(self, msg, pretty=True):
        if pretty:
            msg = self.make_pretty(msg)
        self.qu.put(msg)
        self.messenger.post_message(msg)
        self.__logger.critical(msg)

    def make_pretty(self, msg):
        if isinstance(msg, str):
            return msg
        return pprint.pformat(msg)
