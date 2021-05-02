from workers.THREAD_trader import *

from util.UTIL_dbms import *
from util.UTIL_asset_code import *

from main.TRADE_trade_back import TradeBotUtil
from main.KWDERIV_order_spec import OrderSpec
from main.KWDERIV_live_db_conn import LiveDBCon

from strategy.STRAT_two_to_seven import FTTwoSeven
from strategy.FACTORY_fixed_time import FTFactory, FTManager

from models.MODEL_2to7 import VanillaTradeSVM

from workers.THREAD_event_work import ServerTimeEvent

import sys

from typing import List
from queue import Queue
import pickle
import time
import copy

assert sys.version_info >= (3, 6), f'python version should be 3.6 or higher'


class TradeBot(TradeBotUtil):
    """
    Execute this Bot at 09:01:00
    """
    ymd = '20210430'
    def __init__(self, k:Kiwoom, model:FTManager):
        print('This Module is to purchase 2 ~ 7 Put Option.')
        # Necessary Modules
        super().__init__()
        self.kiwoom = k
        self.spec = OrderSpec(k)
        self.live = LiveDBCon(k)

        # Check directory

        # Train Model Ahead of time
        d = FTFactory()
        # 2 to 7 model
        m_2t7 = VanillaTradeSVM(r'\2to7')
        m_2t7.fit_()
        self.m_2t7_trained = m_2t7.save_model()
        self.m_2t7_tl, self.m_2t7_tlm = d.timing(model)

        a = float(self.get_opening_index()) / 100
        print(a)
        self.atm = self.create_atm(a)
        self.opening = self.get_opening_opt(self.atm)

        # Live Price
        self.live.req_opt_price(asset=self.atm, cols='10')

        # Start Thread
        self.thread_tasks()

        # DB Connect
        loc = r'D:\trade_db\local_trade._db'
        self.localdb = LocalDBMethods2(loc)
        self.localdb.conn.execute("PRAGMA journal_mode=WAL")

        self.iram = MySQLDBMethod(None, 'main')

    def get_opening_index(self) -> str:
        dat = self.spec.minute_price_base()
        res = list()
        for info in dat['멀티데이터']:
            t = self.spec.make_pretty(info['체결시간'])
            if t[:8] == self.ymd:
                res.append(info)
        start = self.spec.make_pretty(res[-1]['시가'])
        return start


    def get_opening_opt(self, asset) -> str:
        dat = self.spec.minute_price_fo(asset)
        res = list()
        for info in dat['멀티데이터']:
            t = self.spec.make_pretty(info['체결시간'])
            if t[:8] == self.ymd:
                res.append(info)
        start = self.spec.make_pretty(res[-1]['시가'])
        return start

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
        tgt = ServerTimeEvent(opening=self.opening,
                              orderspec=self.spec,
                              models=self.m_2t7_trained,
                              asset=self.atm,
                              data_time=self.m_2t7_tl,
                              time_limit=self.m_2t7_tlm)
        # Add Additional Threads
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
    trd = TradeBot(k, FTTwoSeven())
    app.exec()
