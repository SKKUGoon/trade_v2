from workers.THREAD_trader import *

from util.UTIL_dbms import *
from util.UTIL_asset_code import *
from main.TRADE_trade_back import TradeBotUtil
from main.KWDERIV_order_spec import OrderSpec
from main.KWDERIV_live_db_conn import LiveDBCon
from workers.THREAD_event_work import ServerTimeEvent


from strategy import *
from strategy.STRAT_two_to_seven import FTTwoSeven
from strategy.FACTORY_fixed_time import FTFactory
import sys

from typing import List
from queue import Queue
import pickle
import time
import copy

assert sys.version_info >= (3, 6), f'python version should be 3.6 or higher'


class TradeBot(TradeBotUtil):
    def __init__(self, k:Kiwoom, fixed_time_strat:FTManager):
        print('This Module is to purchase 2 ~ 7 Put Option.')
        # Necessary Modules
        super().__init__()
        self.kiwoom = k

        print('Please insert Opening Index >>>')
        a = float(input())
        atm = self.create_atm(a)

        # Helper Modules
        self.spec = OrderSpec(k)
        self.live = LiveDBCon(k)
        self.live.req_opt_price(asset=atm, cols='10')
        self.thread_tasks()
        # Start Time

        # DB Connectivity
        loc = r'D:\trade_db\local_trade._db'
        self.localdb = LocalDBMethods2(loc)
        self.localdb.conn.execute("PRAGMA journal_mode=WAL")

        self.iram = MySQLDBMethod(None, 'main')

    def create_atm(self, index_value, type_='put_option'):
        mat = get_exception_date('MaturityDay')
        target = None
        for days in mat:
            if days[:6] == self.ymd[0:6]:
                print(days, self.ymd)
                target = days

        if target is None:
            raise RuntimeError("Please insert new maturity date.")

        # Before or after the target maturity date
        if self.ymd <= target:
            ba = 'before'
        else:
            ba = 'after'

        asset = asset_code_gen(index_value, type_, datetime.datetime.now(), ba)
        return asset

    def thread_tasks(self):
        threads = QThreadPool.globalInstance().maxThreadCount()
        pool = QThreadPool.globalInstance()
        tgt = ServerTimeEvent(['152510', '152610'])
        pool.start(tgt)


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

    def get_asset(self):
        a = self.spec.tick_price_base()
        print(a)
        ...

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
    trd = TradeBot(k, [FTTwoSeven()])
    app.exec()
