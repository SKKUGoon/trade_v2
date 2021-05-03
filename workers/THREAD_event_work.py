from PyQt5.QtCore import QRunnable, Qt, QThreadPool, pyqtSignal, QObject

from main.KWDERIV_live_db_conn import LiveDBCon
from main.KWDERIV_order_spec import OrderSpec

from data.DATA_2to7_update import *

from util.UTIL_data_convert import *
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

    def __init__(self, orderspec:OrderSpec, live:LiveDBCon, morning:bool, leverage=0.1):
        super().__init__()
        self.morning = morning
        self.order = orderspec
        self.live = live
        parm = FTFactory()
        self.timeline, self.timelimit = parm.timing(FTTwoSeven())

        self.train_models()
        self.get_trade_parmas(leverage)


    def _create_atm(self, values) -> str:
        mat = get_exception_date('MaturityDay')
        for days in mat:
            if self.ymd[:6] == days[:6]:
                m = days  # maturity date in question
                break
        if self.ymd <= m:
            bfaf = 'before'
        else:
            bfaf = 'after'
        atm = asset_code_gen(values, 'put_option', datetime.datetime.now(), bfaf)
        return atm

    def _get_model(self, loc):
        with open(loc, 'rb') as file:
            return pickle.load(file)

    def train_models(self):
        model_tts = VanillaTradeSVM(path_name=r'\2to7')
        model_tts.fit_()
        self.model_loc = model_tts.save_model()
        self.models = list(map(self._get_model, self.model_loc))

    def get_trade_parmas(self, leverage):
        self.money = self.order.get_fo_margin_info(self.order.k.account_num[0])
        self.money = self.money * leverage

        # Model 1 Data
        self.open, self.close = self._get_opening_index()  # CO Return
        self.coret = (self.open - self.close) / self.close
        idx_features = index_features(self.coret, int(self.ymd))
        self.model1_feat = idx_features.loc[int(self.ymd):].to_numpy().tolist()

        # Real Time Price Information
        atm = self._create_atm(self.open)
        self.live.req_opt_price(atm)

        # Model 2 Data
        self.model2_feat = [float(self._get_opening_opt(atm))]

    def _get_opening_index(self) -> str:
        """
        Thread always starts after 09:00:20.
        Parameter start and end will be always defined.
        """
        dat = self.order.minute_price_base()
        res = list()
        for info in dat['멀티데이터']:
            t = self.order.make_pretty(info['체결시간'])
            if t[:8] == self.ymd:
                res.append(info)
        start = self.order.make_pretty(res[-1]['시가'])

        end = self.order.make_pretty(
            dat['멀티데이터'][dat['멀티데이터'].index(res[-1]) + 1]['현재가']  # Day Before's CO Return
        )
        return float(start) / 100, float(end) / 100

    def _get_opening_opt(self, asset) -> str:
        dat = self.order.minute_price_fo(asset)
        res = list()
        for i in dat['멀티데이터']:
            t = self.order.make_pretty(i['체결시간'])
            if t[:8] == datetime.datetime.now().strftime('%Y%m%d'):
                res.append(i)
        start = self.order.make_pretty(res[-1]['시가'])
        return start

    def run(self):
        print(
            f'[THREAD STATUS] >>> TTS Running on {threading.current_thread().getName()}'
        )
        # if self.morning is False:
        #     print(
        #     f'[THREAD STATUS] >>> TTS breaking on {threading.current_thread().getName()}'
        #     )
        #     return

        # Connection to Local Database
        loc = r'D:\trade_db\local_trade._db'
        self.local = LocalDBMethods2(loc)
        self.local.conn.execute("PRAGMA journal_mode=WAL")

        target = 0
        while True:
            time = self.local.select_db(target_table='RT_Option',
                                        target_column=['server_time', 'p_current'])[0]
            real_time = self.local.select_db(target_table='RT',
                                             target_column=['time'])[0][0]

            if time[0] == '0':
                continue  # Kiwoom has yet to send us time.

            if (time[0] >= self.timeline[target]) or (real_time >= self.timelimit[target]):
                self.model2_feat.append(float(time[1]))
                print(time)
                target += 1
            #
            if target == (len(self.timeline)):  # 0 ~ 2 data collected. Exit Loop
                print(
                    f"[{threading.current_thread().getName()}Thread] >>> Model2 feature collected")
                break

        self.model2_feat = get_cumul_return(self.model2_feat)[1:]
        print(self.model2_feat)

        # Gather Data
        cscr_pred = [self.models[0].decision_function(self.model1_feat)[0],
                     self.models[1].decision_function([self.model2_feat])[0]]
        print('model3', cscr_pred)
        if self.models[2].predict([cscr_pred])[0] is True:  # If True, enter market
            print('[THREAD STATUS] >>> TTS Signal On')
            q = self.money // (float(time[1]) * 250000)
            print(q)
            sheet = order_base(name='tts', scr_num='1000', account=self.order.k.account_num[0],
                               asset=self.asset, buy_sell=2, trade_type=3, quantity=q, price=0)
            self.order.send_order_fo(**sheet)
        else:
            print('[THREAD STATUS] >>> TTS Signal Off. Terminating')
            return