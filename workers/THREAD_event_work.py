from PyQt5.QtCore import QRunnable, Qt, QThreadPool

from main.KWDERIV_order_spec import OrderSpec
from util.UTIL_dbms import *
from util.UTIL_notifier import *
from util.set_order import *
from util.UTIL_data_convert import *

from typing import List
import datetime
import threading
import pickle


class ServerTimeEvent(QRunnable):
    def __init__(self, opening, orderspec:OrderSpec, models, asset, data_time:List, time_limit:List):
        super().__init__()
        self.timeline = data_time
        self.timelimit = time_limit
        self.op = opening
        self.order = orderspec
        self.models = models
        self.asset = asset

    def run(self):
        # Connection to Local Database
        loc = r'D:\trade_db\local_trade._db'
        self.local = LocalDBMethods2(loc)
        self.local.conn.execute("PRAGMA journal_mode=WAL")

        # Get
        target = 0
        res = [self.op]
        models = list()

        for ms in self.models:
            with open(ms, 'rb') as f:
                temp = pickle.load(f)
            models.append(temp)

        while True:
            time = self.local.select_db(target_table='RT_Option',
                                        target_column=['server_time', 'p_current'])[0]
            real_time = self.local.select_db(target_table='RT',
                                             target_column=['time'])[0][0]

            if time[0] == '0':
                continue  # Kiwoom has yet to send us time.

            if (time[0] >= self.timeline[target]) or (real_time >= self.timelimit[target]):
                res.append(time[1])
                print(time)
                target += 1

            if target == (len(self.timeline)):  # 0 ~ 2 data collected. Exit Loop
                print(f"[{threading.current_thread().getName()}Thread] >>> Thread exit")
                break

        res = get_cumul_return(
            list(map(lambda x: float(x),res))
        )[1:]

        # Gather Data
        cscr_pred = [models[0].decision_function([[1, 2, 3, 4]])[0],  # TODO: Get CO Return
                     models[1].decision_function([res])[0]]
        if models[2].predict([cscr_pred])[0] is True:  # If True, enter market
            print('Signal On')
            sheet = order_base(name='tts', scr_num='1000', account=self.order.k.account_num[0],
                               asset=self.asset, buy_sell=2, trade_type=3, quantity=1, price=0)
            self.order.send_order_fo(**sheet)
        else:
            print('Signal Off. Terminating')







        # 0분의 정보 받아서
        # SVM까지 여기서 돌리고
        # 1, 0의 결과에 따라 주문까지 넣어놓기
