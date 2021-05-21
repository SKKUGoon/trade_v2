from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from workers.THREAD_trader import *

from util.UTIL_dbms import *
from util.UTIL_asset_code import *

from main.KWDERIV_live_db_conn import LiveDBCon
from main.KW_kiwoom_main import Kiwoom

import matplotlib.pyplot as plt
import numpy as np

import time
import sys

assert sys.version_info >= (3, 6), f'python version should be 3.6 or higher'


class MarketIndice:
    """
    Calculate Real-time Calculated Market Indices
    """
    dt = datetime.datetime.now()
    ymd = datetime.datetime.now().strftime('%Y%m%d')

    tick_index_dict = dict()

    def __init__(self, k:Kiwoom, arg:dict):
        print("This Module Displays Calculated Market Indices")

        self.k = k
        self.live = LiveDBCon.instance(k)

        # Requesting information
        self.req_live_info(arg)
        self.create_index()
        self.create_table()

        self.tick = QTimer(self.k)
        self.tick.start(1000)
        self.tick.timeout.connect(self.tick_index)

        self.bag = QTimer(self.k)
        self.bag.start(1000)
        self.bag.timeout.connect(self.bag_index)

    def create_index(self):
        self.mean_cp = list()
        self.cp = list()
        self.np = list()
        self.ma5 = list()
        self.ma10 = list()  # TODO : Tidy it up

    def create_table(self, name='index_store'):
        dbname = r'D:\trade_db\indice.db'
        self.db = LocalDBMethods2(dbname)
        self.db.conn.execute("PRAGMA journal_mode=WAL")  # To write ahead mode

        var = {
            'time' : 'str',
            'ls' : 'str'
        }
        self.db.create_table(table_name=name, variables=var)

    def req_live_info(self, type_:dict):
        assert all([k in {'index', 'option', 'option_asset'}
                    for k in type_.keys()])
        if type_['index'] is True:
            self.live.req_opt_price('201')
        if type_['option'] is True:
            self.live.req_opt_price(type_['option_asset'])

    def _insert_db(self, name, object, key):
        cond = f"time = '{key}'"
        ex = self.db.select_db(
            target_table=name,
            target_column=['time'],
            condition1=cond
        )

        if ex == []:
            self.db.insert_rows(
                table_name=name,
                col_=self.db.get_column_list(name),
                rows_=[object]
            )
        else:
            self.db.update_rows(
                table_name=name,
                set_ls=['time', 'ls',],
                set_val=[object],
                condition=cond
            )

    def tick_index(self, code='201', price_ind:int=3, table_name='index_store'):
        n = datetime.datetime.now()
        lb = int(n.strftime('%H%M%S')) // 100 * 100
        ub = (int((n + datetime.timedelta(minutes=1)).strftime('%H%M%S'))
              // 100) * 100
        lb, ub = map(str, [lb, ub])
        try:
            if code not in self.k.index_val.keys():
                raise Exception

            if lb in self.tick_index_dict.keys():
                self.tick_index_dict[lb].append(
                    float(self.k.index_val[code][price_ind])
                )
            else:
                self.tick_index_dict = dict()  # Refresh dictionary to save Memory
                self.tick_index_dict[lb] = [
                    float(self.k.index_val[code][price_ind])
                ]

            self._insert_db(
                name=table_name,
                object=[
                    lb,
                    self.tick_index_dict[lb].__repr__() # __repr__ to insert it as str
                ],  # retrieve it with eval()
                key=lb
            )

        except Exception as e:
            print(e)

    def calc_current_position(self, path):
        path = list(map(float, path))
        try:
            return (path[-1] - min(path)) / (max(path) - min(path))
        except ZeroDivisionError:
            return 0

    def bag_index(self, standard:int=5):
        """
        standard in seconds
        090000 will have index from 090010 ~ 090059 (len 50)
        """
        try:
            dats = self.db.select_db(
                target_table='index_store',
                target_column=['*']
            )
            if dats == []:
                raise Exception
        except Exception as e:
            print(e)
            return

        time = sorted([_ for _, __ in dats])
        d = list(map(lambda x: eval(x),
                     [ls for _, ls in dats]))
        assert len(time) == len(d)

        d = sum(d, [])
        start = time[0]

        cp = self.calc_current_position(d)
        self.cp.append(cp)
        if len(self.cp) < standard:
            self.mean_cp.append(np.mean(self.cp))
        else:
            self.mean_cp.append(np.mean(self.cp[-standard:]))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    k = Kiwoom.instance()
    k.connect()
    order = {'index': True, 'option': False}
    trd = MarketIndice(k, order)
    app.exec()