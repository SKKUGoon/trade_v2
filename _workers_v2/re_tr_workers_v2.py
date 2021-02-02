from models.model_config import *
from cmd_test.order_spec import *
from _code.trade_state import individual as individual_trade
from _util._log import *
from models.oms_old_db import *
from PyQt5.QtCore import *

import threading
import pickle


class Trader(QThread):
    state = individual_trade

    get_asset = pyqtSignal(tuple)
    # Signal to main thread

    def __init__(self, model:OMS, time_dict:Dict, trade_value, target_value=None,
                 loss_cut=None, co_token=None, co_pair=None, timeout=None):
        super().__init__()
        self.model = model
        self.time_table = self.set_time_format(time_dict)

        self.name = self.model.strategy

        self.token = co_token
        self.compare = True if co_pair is not None else False

        self.loc = f'./_pickles3/{self.name}_state.pkl'
        status = 0
        self.save_pickle_data(status, self.loc)

    @staticmethod
    def set_time_format(original, to_format='%H%M%S'):
        res = {k: v.strftime(to_format) for k, v in original.items()}
        return res

    @staticmethod
    def save_pickle_data(data, filename: str):
        with open(filename, 'wb') as file:
            pickle.dump(data, file)

    @staticmethod
    def get_pickle_data(filename: str):
        with open(filename, 'rb') as file:
            return pickle.load(file)

    @pyqtSlot()
    def run(self):
        loc = r'C:\Data\local_trade._db'
        self.local = LocalDBMethods2(loc)
        self.local.conn.execute('PRAGMA journal_mode=WAL')

        while self.isRunning():
            status = self.get_pickle_data(self.loc)
            try:
                t = self.local.select_db(target_column=['server_time'],
                                         target_table='RT_Option')[0][0]
                if int(t) == 0:
                    raise Exception
            except Exception:
                t = datetime.datetime.now().strftime('%H%M%S')

            cond_get_asset = ((status == self.state['get_asset']) and
                              (t > self.time_table['get_asset']))
            cond_get_rt_prc = (status == self.state['get_rt_prc'])
            cond_send_compare = (status == self.state['send_main_thread'])
            buy = (status == self.state['buy_asset']) and (t > self.time_table['trade_start'].strftime('%H%M%S'))
            sell = (status == self.state['sell_asset']) and (t > self.time_table['trade_end'].strftime('%H%M%S'))

            print(f'Trader Thread is running on {threading.currentThread().getName()} Running')

            if cond_get_asset:
                self.get_asset.emit(
                    (self.model,)
                )
            if cond_get_rt_prc:
                self.log.emit(
                    (f'{self.name} getting real', None)
                )
            if cond_send_compare:
                self.log.emit(
                    ('I am running', None)
                )


            self.sleep(10)
        # order_oms = {
        #     'rq_name': f'oms{num}',
        #     'screen_num': self.screen_oms,
        #     'account': self.kiwoom.account_num[1],
        #     'code': asset,
        #     'order_type': 1,
        #     'buy_sell': 1,
        #     'trade_type': 1,
        #     'quantity': q,
        #     'price': adj_price,
        #     'order_num': "",
        # }
    ...
