from models.model_config import *
from main.order_spec import *
from _code.trade_state import individual as individual_trade
from _util._log import *
from _util.set_order import OrderSheet
from models.oms_old_db import *
from PyQt5.QtCore import *

import threading
import pickle
from os import path


class Trader(QThread):
    state = individual_trade
    singleshot = [False] * len(state)

    get_asset = pyqtSignal(tuple)
    get_price = pyqtSignal(tuple)
    req_compare = pyqtSignal(tuple)
    log = pyqtSignal(tuple)

    def __init__(self, model:OMS, time_dict:Dict, trade_value, screen_num, order_spec:OrderSpec,
                 target_value=None, loss_cut=None, co_token=None, co_pair=None, timeout=None,
                 start_value=0, test=False):
        super().__init__()
        # Model related Thread parameters
        self.model = model
        self.scr = screen_num
        self.name = self.model.strategy
        self.time_table = self.set_time_format(time_dict)

        # Trade related Thread parameters
        self.loss = loss_cut
        self.maximum = trade_value
        self.halt = target_value
        self.timeout = timeout
        self.sheet = OrderSheet()
        self.spec = order_spec

        # Compare related Thread parameters
        self.token = co_token
        self.compare = True if co_pair is not None else False

        # Status
        self.loc = f'./_pickles3/{self.name}_state.pkl'
        if not path.exists(self.loc):
            status = start_value
            self.save_pickle_data(status, self.loc)
        if test:
            self.save_pickle_data(0, self.loc)

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

    @staticmethod
    def chk_condition(status, target_state, status_dict,
                      time=None, time_status=None, time_table=None, ):
        if time is not None:
            if ((status == status_dict[target_state]) and
                    (time >= time_table[time_status])):
                return True
            else:
                return False
        if time is None:
            if status == status_dict[target_state]:
                return True
            else:
                return False

    @staticmethod
    def __get_rt_price(asset, buysell, localdb:LocalDBMethods2, spec:OrderSpec,
                       from_table='RT_Option', timeout=30):
        col = localdb.get_column_list(from_table)
        time_start = time.time()
        while time.time() - time_start <= timeout:
            try:
                val = localdb.select_db(
                    target_column=col,
                    target_table=from_table,
                    condition1=f"code = '{asset}'"
                )
                price = float(val[0][col.index(buysell)])
                return price
            except Exception:
                continue
            else:
                break
        price = spec.tick_price_fo(asset)
        return price

    def retransact(self, sell_buy:str):
        assert sell_buy in {'sell', 'buy'}

        while True:

            ...

    def get_model_asset(self, model:OMS, name):
        model.get_pred()
        res = model.get_asset()
        file = f'./_pickles3/{name}_asset.pkl'
        self.save_pickle_data(res, file)

    @pyqtSlot()
    def run(self):
        loc = r'C:\Data\local_trade._db'
        self.local = LocalDBMethods2(loc)
        self.local.conn.execute('PRAGMA journal_mode=WAL')

        pickle_base = '../_pickles3/'
        while self.isRunning():
            a, b, c, d, e = False, False, False, False, False
            status = self.get_pickle_data(self.loc)
            try:
                t = self.local.select_db(
                    target_column=['server_time'], target_table='RT_Option')[0][0]
                if int(t) == 0:
                    raise Exception
                self.log.emit((f'{t} is reading from server time', 'debug'))
            except Exception:
                t = datetime.datetime.now().strftime('%H%M%S')
                self.log.emit((f'{t} is reading from local time', 'debug'))

            if self.chk_condition(status, 'get_asset', self.state, t, 'get_asset', self.time_table):
                a = True
                if self.singleshot[status] is False:
                    self.get_asset.emit((self.model, self.name, status+1, self.loc))
                    self.save_pickle_data(status + 1, self.loc)
                    self.singleshot[status] = True

            if self.chk_condition(status, 'get_rt_prc', self.state):
                b = True
                if self.singleshot[status] is False:
                    self.get_price.emit((self.scr, self.name, status+1, self.loc))
                    self.singleshot[status] = True

            if self.chk_condition(status, 'send_main_thread', self.state):
                c = True
                if self.compare is True:
                    if self.singleshot[status] is False:
                        self.req_compare.emit((self.name, self.token, status+1, self.loc))
                        self.signleshot[status] = True
                else:
                    self.save_pickle_data(status+1, self.loc)

            if self.chk_condition(status, 'buy_asset', self.state, t, 'trade_start', self.time_table):
                d = True
                # This Thread
                if self.singleshot[status] is False:
                    ...
                    self.singleshot[status] = True

            if self.chk_condition(status, 'buy_complete', self.state):
                # Go to Main Thread
                if self.singleshot[status] is False:
                    ...
                    self.singleshot[status] = True

            if self.chk_condition(status, 'sell_asset', self.state, t, 'trade_end', self.time_table):
                # This Thread
                if self.singleshot[status] is False:
                    ...
                    self.singleshot[status] = True

            if self.chk_condition(status, 'sell_complete', self.state):
                # Go to Main Thread
                if self.singleshot[status] is False:
                    ...
                    self.singleshot[status] = True

            self.log.emit((f'{self.name} running on {threading.currentThread().getName()}. Model state: {status}', 'debug'))
            self.sleep(1)



