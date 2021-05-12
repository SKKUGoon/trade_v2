from PyQt5.QtCore import QRunnable, QThread

from main.KWDERIV_live_db_conn import LiveDBCon
from main.KWDERIV_order_spec import OrderSpec

from data.DATA_cms_update import *
from data.DATA_00to34_update import prediction

from util.UTIL_dbms import *
from util.UTIL_log import *
from util.UTIL_set_order import *
from util.UTIL_asset_code import *

from strategy.FACTORY_fixed_time import FTFactory
from strategy.STRAT_cms import FTCMS
from strategy.STRAT_zero_to_thirtyfour import FTZeroThirtyFour

import datetime
import threading


class CMS(QRunnable):
    ymd = datetime.datetime.now().strftime('%Y%m%d')

    def __init__(self, orderspec:OrderSpec, live:LiveDBCon,morning:bool, leverage=0.5):
        super().__init__()
        self.morning = morning
        self.order = orderspec
        self.live = live
        self.log = Logger(r'D:\trade_db\log')

        parm = FTFactory()
        self.timeline, self.timelimit, _ = parm.timing(FTCMS())
        self.zttf_timeline, self.zttf_timelimit, _ = parm.timing(FTZeroThirtyFour())
        self.get_trade_params(leverage)

    def get_trade_params(self, leverage):
        self.money = self.order.get_fo_margin_info(self.order.k.account_num[0])
        self.money = self.money * leverage
        self.log.critical(f'[THREAD STATUS] >>> Account Money at {self.money}')

        # Real Time Price Information
        # self.atm = get_today_asset_code()  # execute after 15:00:00
        # self.live.req_opt_price(self.atm)

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
                print('C', res)
                if res == []:
                    raise Exception

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
                print('E', res)
                if res == []:  # The Program hasn't received niether Execution nor Cancellation
                    continue
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
            QThread.sleep(2)
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
                self.true_quant += -unexec
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
        atm = asset_code_gen(values, 'call_option', datetime.datetime.now(), bfaf)
        return atm

    def run(self):
        self.log.debug(
            f'[THREAD STATUS] >>> CMS Running on {threading.current_thread().getName()}'
        )
        if self.morning is True:
            self.log.debug(
                f'[THREAD STATUS] >>> CMS Breaking on {threading.current_thread().getName()}'
            )
            return

        # Connection to Local Database
        loc = r'D:\trade_db\local_trade._db'
        self.local = LocalDBMethods2(loc)
        self.local.conn.execute("PRAGMA journal_mode=WAL")

        # Zero to ThirtyFour Minute
        self.zttf = False
        while True:
            try:
                time = self.local.select_db(
                    target_table='RealTime_Index',
                    target_column=['servertime', 'price'])[0]
            except Exception as e:
                self.log.error(e)
                self.log.error('Index Value Missing. Restart')
                continue

            if time[0] == '0':
                continue

            if time[0] >= self.zttf_timeline[0]:
                atm_3 = float(time[1])
                break

        atm = self._create_atm(atm_3)
        print(atm)
        open59, close59 = (self.order.get_tgtmin_price_fo(atm, self.zttf_timeline[0]),
                           self.order.get_tgtmin_price_fo(atm, self.zttf_timeline[1]))
        self.log.debug(f"Asset: {atm}, Price at {open59}, {close59}")
        self.live.req_opt_price(atm)
        zttf_res = prediction(ATM_index=atm,
                              price_open_1459=open59,
                              price_close_1459=close59)
        print('prediction for', zttf_res.index.tolist()[-1])
        zttf_action, zttf_score = zttf_res.to_numpy().tolist()[-1]
        if zttf_action == 1:
            self.zttf = True
            self.zttf_quant = 0
            self.log.critical(
                f'[THREAD STATUS] >>> ZTTF Signal On. Signal is {zttf_action}, score is {zttf_score}'
            )
            q = self.money // (float(time[1]) * 250000)
            sheet = order_base(name='zttf', scr_num='3000', account=self.order.k.account_num[0],
                               asset=self.atm, buy_sell=2, trade_type=1, quantity=q, price=float(time[1]))
            self.log.critical(f'[THREAD STATUS] >>> (BID) Sending Order {sheet}')
            self.order.send_order_fo(**sheet)
            self.zttf_quant += q
        else:
            self.zttf = False
            self.log.critical(
                f'[THREAD STATUS] >>> ZTTF Signal Off. Signal is {zttf_action}, score is {zttf_score}'
            )


        # Get CMS Data
        path_31_34 = list()
        target = 0
        self.atm = get_today_asset_code()
        while True:
            try:
                cond = f"code = '{self.atm}'"
                time = self.local.select_db(
                    target_table='RT_Option',
                    target_column=['server_time', 'p_current'],
                    condition1=cond)[0]
                real_time = self.local.select_db(
                    target_table='RT',
                    target_column=['time'])[0][0]

            except Exception as e:
                self.log.error(e)
                continue

            if (time[0] == '0') or real_time == []:
                continue

            if (time[0] >= self.timeline[target]) or (real_time >= self.timelimit[target]):
                path_31_34.append(float(time[1]))
                self.log.debug(f'{target + 31}min opening is in >>> {time}')
                target += 1

            if target == (len(self.timeline)):
                self.log.critical(
                    f"[{threading.current_thread().getName()}Thread] >>> CMS Feature collected"
                )
                break
        print('result', path_31_34)
        opt_path_call, opt_path_call_open, co_return = cms_update_data()
        today_pred = cms_prediction(opt_path_call,
                                    co_return,
                                    p31_34=path_31_34)  # New Realtime data
        cms_action = today_pred.to_numpy().tolist()[-1]

        if cms_action[0] == 1:
            if self.zttf is False:
                self.true_quant = 0
                self.log.critical(f'[THREAD STATUS] >>> CMS Signal On. Signal is {cms_action}')
                q = self.money // (float(time[1]) * 250000)
                sheet = order_base(name='cms', scr_num='2000', account=self.order.k.account_num[0],
                                   asset=self.atm, buy_sell=2, trade_type=1, quantity=q, price=float(time[1]))
                self.log.critical(f'[THREAD STATUS] >>> (BID) Sending Order {sheet}')
                self.order.send_order_fo(**sheet)
                self.true_quant += q
            else:
                return  # ZTTF Strategy already bought the same asset as CMS
        else:
            self.log.critical(f'[THREAD STATUS] >>> CMS Signal Off. Terminating. Signal is {cms_action}')
            # TODO sell ZTTF
            sheet = order_base(
                name='zttf', scr_num='3000', account=self.order.k.account_num[0],
                asset=self.atm, buy_sell=1, trade_type=1, quantity=int(self.zttf_quant),
                price=float(time[1]) - 5
            )
            self.order.send_order_fo(**sheet)
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
                self.chk_order('2000', 2, self.atm, q)
                self.log.critical('[THREAD STATUS] >>> (BID) CMS Order Check Done')
                break
            else:
                self.log.error('[THREAD STATUS] >>> CMS Order is not in')
                return
        self.log.critical(
            f'[THREAD STATUS] >>> CMS Strat Resulting Quantity {self.true_quant}'
        )
        return
