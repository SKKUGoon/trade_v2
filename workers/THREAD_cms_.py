from PyQt5.QtCore import QRunnable, Qt, QThreadPool

from main.KWDERIV_order_spec import OrderSpec
from util.UTIL_dbms import *
from util.UTIL_notifier import *
from util.set_order import *
from util.UTIL_data_convert import *

from typing import List
import datetime
import threading
import pickle


class CMS(QRunnable):
    def __init__(self, orderspec:OrderSpec, morning:bool):
        super().__init__()
        self.morning = morning
        self.order = orderspec

    def run(self):
        print(
            f'[THREAD STATUS] >>> CMS Running on {threading.current_thread().getName()}'
        )
        if self.morning is True:
            print(
                f'[THREAD STATUS] >>> CMS breaking on {threading.current_thread().getName()}'
            )
            return
        # Connection to Local Database
        loc = r'D:\trade_db\local_trade._db'
        self.local = LocalDBMethods2(loc)
        self.local.conn.execute("PRAGMA journal_mode=WAL")

        while True:
            # print('running... cms')
            ...


class CMSExt(QRunnable):
    def __init__(self, orderspec:OrderSpec, morning:bool, live):
        super().__init__()
        self.order = orderspec
        self.live = live
        self.morning = morning
        self.money = self.order.get_fo_margin_info(self.order.k.account_num[0])
        self.f()

    def f(self):
        self.live.req_opt_price('201R5425')

    def run(self):
        print(
            f'[THREAD STATUS] >>> CMSExt Running on {threading.current_thread().getName()}'
        )
        if self.morning is False:
            print(
                f'[THREAD STATUS] >>> CMSExt breaking on {threading.current_thread().getName()}'
            )
            return

        # Connection to Local Database
        loc = r'D:\trade_db\local_trade._db'
        self.local = LocalDBMethods2(loc)
        self.local.conn.execute("PRAGMA journal_mode=WAL")

        # Get
        while True:
            time = self.local.select_db(target_table='RT_Option',
                                        target_column=['server_time', 'p_current'])[0]
            real_time = self.local.select_db(target_table='RT',
                                             target_column=['time'])[0][0]

            # if time[0] == '0':
            #     continue
            #
            # if (time[0] >= ...) or (real_time >= ...):
            #     ...

            # print('running... cmsext')

        res = get_cumul_return(
            ...
        )
