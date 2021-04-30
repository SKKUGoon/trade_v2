from workers.THREAD_trader import *

from util.UTIL_dbms import *
from util.UTIL_asset_code import *

from main.TRADE_trade_back import TradeBotUtil
from main.KWDERIV_order_spec import OrderSpec
from main.KWDERIV_live_db_conn import LiveDBCon

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
    def __init__(self, k:Kiwoom):
        print('This Module is to purchase 2 ~ 7 Put Option.')
        # Necessary Modules
        super().__init__()
        self.kiwoom = k
        self.spec = OrderSpec(k)

        # Train Model Ahead of time
        m_2t7 = VanillaTradeSVM(r'\2to7')
        m_2t7.fit_()
        self.m_2t7_trained = m_2t7.save_model()

        print('Please insert Opening Index >>>')
        a = float(input())  # Input index by hand
        self.atm = self.create_atm(a)
        self.opening = self.get_opening(self.atm)

        # Helper Modules

        self.live = LiveDBCon(k)
        self.live.req_opt_price(asset=self.atm, cols='10')
        self.thread_tasks()
        # Start Time

        # DB Connectivity
        loc = r'D:\trade_db\local_trade._db'
        self.localdb = LocalDBMethods2(loc)
        self.localdb.conn.execute("PRAGMA journal_mode=WAL")

        self.iram = MySQLDBMethod(None, 'main')

    def get_opening(self, asset) -> str:
        dat = self.spec.minute_price_fo(asset)
        res = list()
        for i in dat['멀티데이터']:
            t = self.spec.make_pretty(i['체결시간'])
            if t[:8] == datetime.datetime.now().strftime('%Y%m%d'):
                res.append(i)
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
        tgt = ServerTimeEvent(self.opening,
                              self.spec,
                              self.m_2t7_trained,
                              self.atm,
                              ['144200', '144300'])

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
    trd = TradeBot(k)
    app.exec()
