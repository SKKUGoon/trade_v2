from workers.THREAD_trader import *

from util.UTIL_dbms import *
from main.TRADE_trade_back import TradeBotUtil

import sys

from typing import List
from queue import Queue
import pickle
import time
import copy

assert sys.version_info >= (3, 6), f'python version should be 3.6 or higher'


class TradeBot(TradeBotUtil):

    def __init__(self, k:Kiwoom, fixed_time_strat:int):
        # Necessary Modules
        super().__init__()
        self.kiwoom = k
        self.spec = OrderSpec(k)

        # DB Connectivity
        loc = r'C:\Data\local_trade._db'
        self.localdb = LocalDBMethods2(loc)
        self.localdb.conn.execute("PRAGMA journal_mode=WAL")


    def thread_log(self, signal: tuple):
        msg, level = signal
        if level.lower() == 'debug':
            self.log.debug(msg)
        elif level.lower() == 'critical':
            self.log.critical(msg)
        elif level.lower() == 'warning':
            self.log.warning(msg)
        elif level.lower() == 'error':
            self.log.error(msg)

    def set_standard_time(self):
        ...

    def get_rt_prc(self, signal: str):
        ...


if __name__ == '__main__':
    app = QApplication(sys.argv)
    k = Kiwoom.instance()
    for i in range(10):
        try:
            k.connect()
        except:
            print('kiwoom connect retry')
            time.sleep(10)
        else:
            break

    app.exec()
