from PyQt5.QtCore import QRunnable, Qt, QThreadPool, pyqtSignal, QObject, QTimer

from main.KWDERIV_live_db_conn import LiveDBCon
from main.KWDERIV_order_spec import OrderSpec

from data.DATA_2to7_update import *

from util.UTIL_data_convert import *
from util.UTIL_log import Logger
from util.UTIL_notifier import *
from util.UTIL_dbms import *
from util.UTIL_asset_code import *
from util.set_order import *

from models.MODEL_2to7 import VanillaTradeSVM

from strategy.STRAT_two_to_seven import FTTwoSeven
from strategy.FACTORY_fixed_time import FTFactory

from typing import List
import datetime
import threading
import pickle
import time

class TwoToSeven(QRunnable):
    ymd = datetime.datetime.now().strftime('%Y%m%d')

    def __init__(self):
        super().__init__()

    def re_trade(self, screen_num, sellbuy, asset):
        try:
            col = ['TICKER', 'ORDER_QTY', 'ORDER_PRICE', 'UNEX_QTY', 'ORDER_NO', 'TRAN_QTY']
            cond = f"SCREEN_NUM = '{screen_num}'"

            res = self.local.select_db(
                target_column=col, target_table='RT_TR_E', condition1=cond
            )[0]

            tran_qty = res[col.index('TRAN_QTY')]
            if tran_qty == '':
                raise Exception

        except Exception as e:
            col = ['TICKER', 'ORDER_QTY', 'ORDER_PRICE', 'UNEX_QTY', 'ORDER_NO']
            cond = f"SCREEN_NUM = '{screen_num}'"
            res = self.local.select_db(
                target_column=col, target_table='RT_TR_E', condition1=cond
            )
            tran_qty = ''

        unexec = int(res[col.index('UNEX_QTY')])
        orginal = res[col.index('ORDER_NO')]

        if unexec == 0 and tran_qty != '':
            return

        else:
            cancel = order_base(name='tts', scr_num=screen_num, account=self.order.k.account_num[0],
                                asset=asset, buy_sell=2, trade_type=3, quantity=int(unexec),
                                order_type=3, price=0)
            self.order.send_order_fo(**cancel)
            new_quantity = ...
            cancel = order_base(name='tts', scr_num=screen_num, account=self.order.k.account_num[0],
                                asset=asset, buy_sell=2, trade_type=3, quantity=new_quantity,
                                order_type=1, price=0)


    def run(self):
        loc = r'D:\trade_db\local_trade._db'
        self.local = LocalDBMethods2(loc)
        self.local.conn.execute("PRAGMA journal_mode=WAL")

        while True:
            try:
                submitted = self.local.select_db(
                    target_table='RT_TR_S', target_column=['ORDER_STATUS']
                )[0][0]
            except Exception as e:
                submitted = None
            if submitted == '접수':
                self.re_trade()
                ...
            else:
                ...