from models.model_config import *
from main.KWDERIV_order_spec import *
from _code.trade_state import individual as individual_trade
from _util.UTIL_log import *
from _util.set_order import OrderSheet
from models.oms_v1 import *
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

    def __init__(self, model:OMS, time_dict:Dict, trade_value, screen_num, order_spec:OrderSpec,
                 target_value=None, loss_cut=None, co_pair=False, timeout=None):
        super().__init__()
        # Model related Thread parameters
        self.model = model
        self.scr = screen_num
        self.name = self.model.strategy
        self.time_table = self.set_time_format(time_dict)
        print(f"{self.name}'s token number is {self.model.token['token_number']}")

        # Trade related Thread parameters
        self.loss = loss_cut
        self.maximum = trade_value
        self.halt = target_value
        self.timeout = timeout
        self.sheet = OrderSheet()
        self.spec = order_spec

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
            status = self.local.select_db(
                target_column=['trade_status'],
                target_table='trade_state',
                condition1=f"model_name='{self.name}'"
            )[0][0]
            try:
                t = self.local.select_db(
                    target_column=['server_time'], target_table='RT_Option')[0][0]
                if int(t) == 0:
                    raise Exception
            except Exception:
                t = datetime.datetime.now().strftime('%H%M%S')

            if self.chk_condition(status, 'get_asset_buy', self.state, t, 'get_asset', self.time_table):
                if self.singleshot[status] is False:
                    ex = copy.deepcopy(self.singleshot)
                    self.get_asset.emit(
                        (self.model, self.name, self.loc, ex, status+1)
                    )
                    self.set_state(self.local, status+1, self.name)
                    self.singleshot[status] = True
                else:
                    self.log.emit((f'{self.name} get_asset_buy already done', 'debug'))

            if self.chk_condition(status, 'get_rt_prc', self.state):
                if self.singleshot[status] is False:
                    ex = copy.deepcopy(self.singleshot)
                    self.get_price.emit(
                        (self.scr, self.name, self.loc, ex, status+1)
                    )
                    self.singleshot[status] = True
                else:
                    self.log.emit((f'{self.name} get_rt_prc already done', 'debug'))

            if self.chk_condition(status, 'send_main_thread', self.state):
                if self.compare is True:
                    if self.singleshot[status] is False:
                        self.req_compare.emit((self.name, self.token, status+1))
                        self.signleshot[status] = True
                else:
                    self.set_state(self.local, status+1, self.name)

            if self.chk_condition(status, 'buy_asset', self.state, t, 'trade_start', self.time_table):
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



        # self.local_event_loop = QEventLoop()
        # self.timer = QTimer(self)
        # self.timer.singleShot(3000, self.login_callback)
        # self.local_event_loop.exec()            # 이 라인에서 self.local_event_loop가 quit될 때까지 대기 (이벤트는 처리됨)
        # self.check_balance()

