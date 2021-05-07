from PyQt5.QtCore import QRunnable, QThread

from main.KWDERIV_live_db_conn import LiveDBCon
from main.KWDERIV_order_spec import OrderSpec

from data.DATA_cms_update import *

from util.UTIL_dbms import *
from util.UTIL_log import *
from util.UTIL_set_order import *
from util.UTIL_data_convert import *

from strategy.FACTORY_fixed_time import FTFactory
from strategy.STRAT_cms_ext import FTCMSExt
from typing import List
import datetime
import threading
import pickle

class CMSExt(QRunnable):
    def __init__(self, orderspec:OrderSpec, morning:bool, live):
        super().__init__()
        self.order = orderspec
        self.live = live
        self.morning = morning
        self.log = Logger(r'D:\trade_db\log')
        parm = FTFactory()


    def run(self):
        print(
            f'[THREAD STATUS] >>> CMSExt Running on {threading.current_thread().getName()}'
        )
        if self.morning is False:
            print(
                f'[THREAD STATUS] >>> CMSExt breaking on {threading.current_thread().getName()}'
            )
            return
        return
        # Connection to Local Database
        loc = r'D:\trade_db\local_trade._db'
        self.local = LocalDBMethods2(loc)
        self.local.conn.execute("PRAGMA journal_mode=WAL")