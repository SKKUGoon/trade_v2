from main.KWDERIV_order_spec import *
from code_.trade_state import individual as individual_trade
from util.UTIL_log import *
from util.set_order import OrderSheet
from PyQt5.QtCore import *

import copy
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

    def __init__(self, model, time_dict:Dict, trade_value, screen_num, order_spec:OrderSpec,
                 target_value=None, loss_cut=None, co_pair=False, timeout=None):
        super().__init__()

        # Compare related Thread parameters
        self.compare = co_pair
        self.token_num = self.model.token['token_number']

        # Status
        self.loc = f'./_pickles3/token{self.token_num}/'
        if not path.exists(self.loc):
            os.mkdir(self.loc)

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

    def create_model_status(self, localdb:LocalDBMethods2, model_name, table_name='trade_state'):
        param = {'model_name': 'Varchar(20)', 'trade_status': 'int'}
        localdb.create_table(
            table_name=table_name, variables=param
        )
        count = localdb.count_rows(table_name, condition=f"model_name='{model_name}'")
        if count == 0:
            localdb.insert_rows(
                table_name,
                col_=list(param.keys()),
                rows_=[[model_name, self.state['get_asset_buy']]])

    def set_state(self, localdb, state, model_name):
        localdb.update_rows(
            table_name='trade_state',
            set_ls=['trade_status'],
            set_val=[[state]],
            condition=f"model_name='{model_name}'"
        )

    def retransact(self, sell_buy:str):
        assert sell_buy in {'sell', 'buy'}

        while True:

            ...

    @pyqtSlot()
    def run(self):
        loc = r'C:\Data\local_trade._db'
        self.local = LocalDBMethods2(loc)
        self.local.conn.execute('PRAGMA journal_mode=WAL')
        self.create_model_status(self.local, self.name)

        while self.isRunning():
            ...
