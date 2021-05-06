from PyQt5.QtCore import QRunnable, QThread

from main.KWDERIV_live_db_conn import LiveDBCon
from main.KWDERIV_order_spec import OrderSpec

from data.DATA_2to7_update import *

from util.UTIL_data_convert import *
from util.UTIL_log import Logger
from util.UTIL_dbms import *
from util.UTIL_asset_code import *
from util.UTIL_set_order import *

from models.MODEL_2to7 import VanillaTradeSVM

from strategy.STRAT_two_to_seven import FTTwoSeven
from strategy.FACTORY_fixed_time import FTFactory

import datetime
import threading
import pickle


class TwoToSeven(QRunnable):
    ymd = datetime.datetime.now().strftime('%Y%m%d')

    def __init__(self, orderspec:OrderSpec, live:LiveDBCon, morning:bool, leverage=0.5):
        super().__init__()
        self.morning = morning
        self.order = orderspec
        self.live = live
        self.log = Logger(r'D:\trade_db\log')
        parm = FTFactory()
        self.timeline, self.timelimit, self.end = parm.timing(FTTwoSeven())
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
        self.log.critical(f'[THREAD STATUS] >>> Account Money at {self.money}')

        # Model 1 Data
        self.open, self.close = self._get_opening_index()  # CO Return
        self.coret = (self.open - self.close) / self.close
        idx_features = index_features(self.coret, int(self.ymd))
        self.model1_feat = idx_features.loc[int(self.ymd):].to_numpy().tolist()

        # Real Time Price Information
        self.atm = self._create_atm(self.open)
        self.live.req_opt_price(self.atm)

        # Model 2 Data
        self.model2_feat = [float(self._get_opening_opt(self.atm))]

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

    def chk_cancel(self, screen_num, sellbuy, asset, original, original_unexec) -> any:
        self.log.critical("Checking Cancellation")
        while True:
            QThread.sleep(1)
            try:
                cond = f"SCREEN_NUM = '{screen_num}' and SELL_BUY_GUBUN = " \
                       f"'{sellbuy}' and ORIGINAL_ORDER_NO = '{int(original)}'"
                res = self.local.select_db(
                    target_column=['ORDER_STATUS', 'ORDER_QTY'],
                    target_table='RT_TR_C',
                    condition1=cond
                )
                if res[0][0] != '확인':
                    raise Exception

            except Exception as e:
                cond = f"SCREEN_NUM = '{screen_num}' and SELL_BUY_GUBUN = " \
                       f"'{sellbuy}' and ORDER_NO = '{original}'"
                res = self.local.select_db(
                    target_column=['UNEX_QTY'],
                    target_table='RT_TR_E',
                    condition1=cond
                )
                have_quantity = int(res[0][0])
                if have_quantity == 0:
                    return 0
                self.true_quant = self.true_quant + original_unexec - have_quantity
                cancel = order_base(name='tts', scr_num=screen_num, account=self.order.k.account_num[0],
                                    asset=asset, buy_sell=sellbuy, trade_type=3, quantity=int(have_quantity),
                                    order_type=3, price=0, order_num=original)
                self.order.send_order_fo(**cancel)
                continue
            else:
                return res[0][1]


    def chk_order(self, screen_num, sellbuy, asset, original_q):
        self.log.critical("Checking Not-executed Orders.")

        while True:
            QThread.sleep(1)
            try:
                col = ['TICKER', 'ORDER_QTY', 'ORDER_PRICE', 'UNEX_QTY', 'ORDER_NO', 'TRAN_QTY']
                cond = f"SCREEN_NUM = '{screen_num}' and SELL_BUY_GUBUN = '{sellbuy}'"

                res = self.local.select_db(
                    target_column=col, target_table='RT_TR_E', condition1=cond
                )[0]

                tran_qty = res[col.index('TRAN_QTY')]
                if tran_qty == '':
                    raise Exception

            except Exception as e:  # Couldn't execute single order
                col = ['TICKER', 'ORDER_QTY', 'ORDER_PRICE', 'UNEX_QTY', 'ORDER_NO']
                cond = f"SCREEN_NUM = '{screen_num}' and SELL_BUY_GUBUN = '{sellbuy}'"
                res = self.local.select_db(
                    target_column=col, target_table='RT_TR_S', condition1=cond
                )[0]
                tran_qty = ''

            unexec, original, order_price = (
                int(res[col.index('UNEX_QTY')]),
                res[col.index('ORDER_NO')],
                float(res[col.index('ORDER_PRICE')])
            )
            if unexec == 0 and tran_qty != '':
                return

            else:
                cancel = order_base(name='tts', scr_num=screen_num, account=self.order.k.account_num[0],
                                    asset=asset, buy_sell=sellbuy, trade_type=3, quantity=int(unexec),
                                    order_type=3, price=0, order_num=original)
                self.order.send_order_fo(**cancel)
                self.true_quant += -(unexec)
                real_cancel = self.chk_cancel(
                    screen_num, sellbuy, asset, original, unexec
                )
                time = self.local.select_db(target_table='RT_Option',
                                            target_column=['server_time', 'p_current'])[0]

                try:
                    assert int(real_cancel) == int(unexec)  # If chk_cancel changed the cancelled value
                except Exception as e:
                    print(e)
                    unexec = int(real_cancel)

                # New Money and Quantity after an iteration.
                self.money = (self.money - ((original_q - unexec) * 250000) * order_price)
                new_quantity = self.money // (float(time[1]) * 250000)  # spent
                original_q = new_quantity

                new_order = order_base(name='tts', scr_num=screen_num, account=self.order.k.account_num[0],
                                       asset=asset, buy_sell=sellbuy, trade_type=1, quantity=new_quantity,
                                       order_type=1, price=float(time[1]))
                self.true_quant += new_quantity
                self.order.send_order_fo(**new_order)

    def run(self):
        self.log.debug(
            f'[THREAD STATUS] >>> TTS Running on {threading.current_thread().getName()}'
        )
        if self.morning is False:
            self.log.debug(
            f'[THREAD STATUS] >>> TTS breaking on {threading.current_thread().getName()}'
            )
            return

        # Connection to Local Database
        loc = r'D:\trade_db\local_trade._db'
        self.local = LocalDBMethods2(loc)
        self.local.conn.execute("PRAGMA journal_mode=WAL")

        # Gather Data
        target = 0
        while True:
            try:
                time = self.local.select_db(target_table='RT_Option',
                                            target_column=['server_time', 'p_current'])[0]
                real_time = self.local.select_db(target_table='RT',
                                                 target_column=['time'])[0]
            except Exception as e:
                self.log.error(e)
                continue

            if time[0] == '0' or real_time == []:
                continue  # Kiwoom has yet to send us time.

            if (time[0] >= self.timeline[target]) or (real_time[0] >= self.timelimit[target]):
                self.model2_feat.append(float(time[1]))
                self.log.debug(f'{target + 1}min opening is in >>> {time}')
                target += 1

            if target == (len(self.timeline)):  # 0 ~ 2 data collected. Exit Loop
                self.log.critical(
                    f"[{threading.current_thread().getName()}Thread] >>> Model2 feature collected"
                )
                break

        self.model2_feat = get_cumul_return(self.model2_feat)[1:]
        cscr_pred = [self.models[0].decision_function(self.model1_feat)[0],
                     self.models[1].decision_function([self.model2_feat])[0]]
        final_pred = self.models[2].predict([cscr_pred])[0]  # If True, enter market
        # Bid
        if final_pred is True or final_pred == 1:
            self.true_quant = 0
            self.log.critical(f'[THREAD STATUS] >>> TTS Signal On. Signal is {final_pred}')
            q = self.money // (float(time[1]) * 250000)
            sheet = order_base(name='tts', scr_num='1000', account=self.order.k.account_num[0],
                               asset=self.atm, buy_sell=2, trade_type=1, quantity=q, price=float(time[1]))
            self.log.critical(f'[THREAD STATUS] >>> (BID) Sending Order {sheet}')
            self.order.send_order_fo(**sheet)
            self.true_quant += q
        else:
            self.log.critical(f'[THREAD STATUS] >>> TTS Signal Off. Terminating. Signal is {final_pred}')
            return

        # Check Order
        while True:
            try:
                cond = f"SCREEN_NUM='1000'"
                submitted = self.local.select_db(
                    target_table='RT_TR_S', target_column=['ORDER_STATUS'], condition1=cond
                )[0][0]
            except Exception as e:
                continue

            if submitted == '접수':
                self.log.critical('[THREAD STATUS] >>> (BID) TTS Order is in')
                self.chk_order('1000', 2, self.atm, q)
                self.log.critical('[THREAD STATUS] >>> (BID) TTS Order Check Done')
                break
            else:
                self.log.error('[THREAD STATUS] >>> TTS Order is not in')
                return
        self.log.critical(
            f'[THREAD STATUS] >>> TTS Strat Resulting Quantity {self.true_quant}'
        )

        # Ask
        while True:
            time = self.local.select_db(target_table='RT_Option',
                                        target_column=['server_time', 'p_current'])[0]
            real_time = self.local.select_db(target_table='RT',
                                             target_column=['time'])[0][0]

            if real_time >= self.end[0]:  # at 7min
                sheet = order_base(
                    name='tts', scr_num='1100', account=self.order.k.account_num[0],
                    asset=self.atm, buy_sell=1, trade_type=1, quantity=int(self.true_quant), price=float(time[1])
                )
                self.log.critical(f'[THREAD STATUS] >>> (ASK) Sending Order {sheet}')
                self.order.send_order_fo(**sheet)
                break

        # # Check Order
        # while True:
        #     try:
        #         cond = f"SCREEN_NUM='1100'"
        #         submitted = self.local.select_db(
        #             target_table='RT_TR_S', target_column=['ORDER_STATUS'], condition1=cond
        #         )[0][0]
        #     except Exception as e:
        #         continue
        #
        #     if submitted == '접수':
        #         self.log.critical('[THREAD STATUS] >>> (ASK) TTS Order is in')
        #         self.chk_order('1100', 1, self.atm, have_quantity)
        #     else:
        #         self.log.error('[THREAD STATUA] >>> TTS Order is not in')
        #         return