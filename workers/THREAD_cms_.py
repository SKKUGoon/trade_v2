from PyQt5.QtCore import QRunnable, QThread

from main.KWDERIV_live_db_conn import LiveDBCon
from main.KWDERIV_order_spec import OrderSpec

from data.DATA_cms_update import *

from util.UTIL_dbms import *
from util.UTIL_log import *
from util.UTIL_set_order import *
from util.UTIL_data_convert import *

from strategy.FACTORY_fixed_time import FTFactory
from strategy.STRAT_cms import FTCMS, FTCMSExt
from typing import List
import datetime
import threading
import pickle


class CMSExt(QRunnable):
    ymd = datetime.datetime.now().strftime('%Y%m%d')

    def __init__(self, orderspec:OrderSpec, live:LiveDBCon,morning:bool, leverage=0.5):
        super().__init__()
        self.morning = morning
        self.order = orderspec
        self.live = live
        self.log = Logger(r'D:\trade_db\log')

        parm = FTFactory()
        self.timeline, self.timelimit, _ = parm.timing(FTCMS())

    def get_trade_params(self, leverage):
        self.money = self.order.get_fo_margin_info(self.order.k.account_num[0])
        self.money = self.money * leverage
        self.log.critical(f'[THREAD STATUS] >>> Account Money at {self.money}')

        # Real Time Price Information
        self.atm = get_today_asset_code()  # execute after 15:00:00
        self.live.req_opt_price(self.atm)

    def run(self):
        print(
            f'[THREAD STATUS] >>> CMS Running on {threading.current_thread().getName()}'
        )
        if self.morning is True:
            print(
                f'[THREAD STATUS] >>> CMS Breaking on {threading.current_thread().getName()}'
            )
            return
        return
        # Connection to Local Database
        loc = r'D:\trade_db\local_trade._db'
        self.local = LocalDBMethods2(loc)
        self.local.conn.execute("PRAGMA journal_mode=WAL")

        # Get
        path_31_34 = list()
        target = 0
        while True:
            try:
                time = self.local.select_db(target_table='RT_Option',
                                            target_column=['server_time', 'p_current'])[0]
                real_time = self.local.select_db(target_table='RT',
                                                 target_column=['time'])[0][0]

            except Exception as e:
                self.log.error(e)
                continue

            if time[0] == '0' or real_time == []:
                continue

            if (time[0] >= seljf.timeline[target]) or (real_time >= self.timelimit[target]):
                path_31_34.append(float(time[1]))
                self.log.debug(f'{target + 31}min opening is in >>> {time}')
                target += 1

            if target == (len(self.timeline)):
                self.log.critical(
                    f"[{threading.current_thread().getName()}Thread] >>> CMS Feature collected"
                )
                break

        opt_path_call, opt_path_call_open, co_return = cms_update_data()
        today_pred = cms_prediction(opt_path_call,
                                    co_return,
                                    p31_34=path_31_34)  # New Realtime data
        action = today_pred.to_numpy().tolist()[-1]

        if action[0] == 1:
            self.true_quant = 0
            self.log.critical(f'[THREAD STATUS] >>> CMS Signal On. Signal is {action}')
            q = self.money // (float(time[1]) * 250000)
            sheet = order_base(name='cms', scr_num='2000', account=self.order.k.account_num[0],
                               asset=self.atm, buy_sell=2, trade_type=1, quantity=q, price=float(time[1]))
            self.log.critical(f'[THREAD STATUS] >>> (BID) Sending Order {sheet}')
            self.order.send_order_fo(**sheet)
            self.true_quant += q
        else:
            self.log.critical(f'[THREAD STATUS] >>> CMS Signal Off. Terminating. Signal is {action}')
            return

            # Check Order
        while True:
            try:
                cond = f"SCREEN_NUM='2000'"
                submitted = self.local.select_db(
                    target_table='RT_TR_S', target_column=['ORDER_STATUS'], condition1=cond
                )[0][0]
            except Exception as e:
                continue

            if submitted == '접수':
                self.log.critical('[THREAD STATUS] >>> (BID) CMS Order is in')
                # TODO: insert Check Order function
                self.log.critical('[THREAD STATUS] >>> (BID) CMS Order Check Done')
                break
            else:
                self.log.error('[THREAD STATUS] >>> CMS Order is not in')
                return
        self.log.critical(
            f'[THREAD STATUS] >>> CMS Strat Resulting Quantity {self.true_quant}'
        )


class CMS(QRunnable):
    def __init__(self, orderspec:OrderSpec, morning:bool, live):
        super().__init__()
        self.order = orderspec
        self.live = live
        self.morning = morning

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
