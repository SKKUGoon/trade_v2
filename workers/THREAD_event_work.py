from PyQt5.QtCore import QRunnable, Qt, QThreadPool

from main.KWDERIV_order_spec import OrderSpec
from util.UTIL_dbms import *
from util.UTIL_notifier import *
from util.UTIL_data_convert import *

from typing import List
import datetime
import threading



class ServerTimeEvent(QRunnable):
    def __init__(self, opening, orderspec:OrderSpec, data_time:List):
        super().__init__()
        self.timeline = data_time
        self.op = opening
        self.order = orderspec

    def run(self):
        loc = r'D:\trade_db\local_trade._db'
        self.local = LocalDBMethods2(loc)
        self.local.conn.execute("PRAGMA journal_mode=WAL")
        target = 0
        res = [self.op]
        while True:
            time = self.local.select_db(
                target_table='RT_Option',
                target_column=['server_time', 'p_current']
            )[0]

            if time[0] == '0':
                # Kiwoom has yet to send us time.
                continue

            if time[0] >= self.timeline[target]:
                res.append(time[1])
                print(time)
                target += 1

            if target == (len(self.timeline)):
                print(
                    f"[{threading.current_thread().getName()}Thread] >>> Thread exit"
                )
                break

        res = get_cumul_return(
            list(map(lambda x: float(x),
                     res))
        )[1:]

        print(res)
        # 0분의 정보 받아서
        # SVM까지 여기서 돌리고
        # 1, 0의 결과에 따라 주문까지 넣어놓기
