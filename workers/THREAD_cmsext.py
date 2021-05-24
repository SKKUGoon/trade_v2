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
    def __init__(self, orderspec:OrderSpec, live:LiveDBCon, morning:bool, cmsext:bool):
        super().__init__()
        self.order = orderspec
        self.live = live
        self.morning = morning
        self.log = Logger(r'D:\trade_db\log')
        self.ext = cmsext
        parm = FTFactory()
        __, self.market_start, self.timeline = parm.timing(FTCMSExt())
        self.trade = self.get_trade_param()
        print(self.trade)

    def get_trade_param(self) -> Dict:
        have, _ = self.order.get_fo_deposit_info(
            self.order.k.account_num[0]
        )
        res = dict()
        for asset_info in have:
            asset = asset_info['asset_code']
            asset_q = int(asset_info['quantity'])

            # Real Time Price Req
            self.live.req_opt_price(asset)

            # Selling price for Each Asset
            prc = 0.0
            if self.ext is False:
                prc = self.order.tick_price_fo(asset)  # float

            res[asset] = [asset_q, prc]

        return res

    def chk_cancel(self, screen_num, sellbuy, asset, original, original_unexec) -> any:
        self.log.critical("Checking Cancellation")
        while True:
            QThread.sleep(1)
            try:
                self.log.debug("Ping RT_TR_C")
                cond = f"SCREEN_NUM = '{screen_num}' and SELL_BUY_GUBUN = " \
                       f"'{sellbuy}' and ORIGINAL_ORDER_NO = '{int(original)}'"
                res = self.local.select_db(
                    target_column=['ORDER_STATUS', 'ORDER_QTY'],
                    target_table='RT_TR_C',
                    condition1=cond
                )
                if res == []:
                    raise Exception

                if res[0][0] != '확인':
                    raise Exception

            except Exception as e:
                self.log.debug("Ping RT_TR_E, instead")
                cond = f"SCREEN_NUM = '{screen_num}' and SELL_BUY_GUBUN = " \
                       f"'{sellbuy}' and ORDER_NO = '{original}'"
                res = self.local.select_db(
                    target_column=['UNEX_QTY'],
                    target_table='RT_TR_E',
                    condition1=cond
                )
                if res == []:  # The Program hasn't received neither Execution nor Cancellation
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
                print(res)
                return res[0][1]

    def chk_submit(self, screen_num:str, order_quant:int, buy_sell:int, asset, strategy_name:str='COExt'):
        # Check Order
        while True:
            try:
                cond = f"SCREEN_NUM='{screen_num}'"
                submitted = self.local.select_db(
                    target_table='RT_TR_S', target_column=['ORDER_STATUS'], condition1=cond
                )[0][0]
            except Exception as e:
                continue

            if submitted == '접수':
                self.log.critical(f'[THREAD STATUS] >>> (BID) {strategy_name} Order is in')
                self.chk_order(screen_num, buy_sell, asset, order_quant)
                self.log.critical(f'[THREAD STATUS] >>> (BID) {strategy_name} Order Check Done')
                break
            else:
                self.log.error(f'[THREAD STATUS] >>> {strategy_name} Order is not in')
                return
        self.log.critical(
            f'[THREAD STATUS] >>> {strategy_name} Resulting Quantity {0}'
        )

    def chk_order(self, screen_num, sellbuy, asset, original_q):
        self.log.critical("Checking Not-executed Orders.")

        while True:
            QThread.sleep(4)
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
                print(cond)
                res = self.local.select_db(
                    target_column=col, target_table='RT_TR_S', condition1=cond
                )[0]
                print(res)
                tran_qty = ''

            unexec, original, order_price = (
                int(res[col.index('UNEX_QTY')]),
                res[col.index('ORDER_NO')],
                float(res[col.index('ORDER_PRICE')])
            )
            if unexec == 0 and tran_qty != '':
                return

            else:
                print(f'unexc {unexec}, orgi {original}, ord_prc {order_price}')
                cancel = order_base(name='cmsext', scr_num=screen_num, account=self.order.k.account_num[0],
                                    asset=asset, buy_sell=sellbuy, trade_type=3, quantity=int(unexec),
                                    order_type=3, price=0, order_num=original)
                self.order.send_order_fo(**cancel)
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

                new_order = order_base(name='cmsext', scr_num=screen_num, account=self.order.k.account_num[0],
                                       asset=asset, buy_sell=sellbuy, trade_type=3, quantity=unexec,
                                       order_type=1, price=0)
                self.order.send_order_fo(**new_order)

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

        if self.ext is True:
            self.log.critical(f'[THREAD STATUS] >>> CMSEXT Signal is True')
            sell_t = self.timeline[1]
            while True:
                if datetime.datetime.now().strftime('%H%M%S') >= sell_t:
                    for a, qp in self.trade.items():
                        q, p = qp
                        if int(q) == 0:
                            continue
                        sheet = order_base(name='cmsext', scr_num='4000', account=self.order.k.account_num[0],
                                           asset=a, buy_sell=1, order_type=4, trade_type=1, quantity=q, price=0)
                        self.log.critical(f'[THREAD STATUS] >>> (ASK) Sending Order {sheet}')
                        self.order.send_order_fo(**sheet)
                    break

        else:
            sell_t = self.timeline[0]
            while True:
                self.log.critical(f'[THREAD STATUS] >>> CMSEXT Signal is False')
                if True or datetime.datetime.now().strftime('%H%M%S') >= sell_t:
                    for a, qp in self.trade.items():
                        q, p = qp
                        if int(q) == 0:
                            continue
                        sheet = order_base(name='cmsext', scr_num='4000', account=self.order.k.account_num[0],
                                           asset=a, buy_sell=1, trade_type=1, quantity=q, price=p)
                        self.log.critical(f'[THREAD STATUS] >>> (ASK) Sending Order {sheet}')
                        self.order.send_order_fo(**sheet)

                    break

        # Check Order
        while True:
            if datetime.datetime.now().strftime('%H%M%S') >= '121500': #self.market_start[0]:
                break  # Wait until Market start

        for a, qp in self.trade.items():
            q, p = qp
            self.chk_submit(screen_num='4000',
                            order_quant=q,
                            buy_sell=1,
                            asset=a)

        return