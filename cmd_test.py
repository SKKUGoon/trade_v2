from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from workers.THREAD_trader import *

from util.UTIL_dbms import *
from util.UTIL_asset_code import *

from main.TRADE_trade_back import TradeBotUtil
from main.KWDERIV_order_spec import OrderSpec
from main.KWDERIV_live_db_conn import LiveDBCon
from main.KW_kiwoom_main import Kiwoom
from main.TRADE_trade_main import TradeBot
from workers.THREAD_tts import TwoToSeven
from workers.THREAD_cms_ import CMS
from workers.THREAD_cmsext import CMSExt

import time
import sys

assert sys.version_info >= (3, 6), f'python version should be 3.6 or higher'

if __name__ == '__main__':
    app = QApplication(sys.argv)
    k = Kiwoom.instance()
    for i in range(10):
        try:
            k.connect()
        except:
            print('kiwoom connect retry')
            time.sleep(10)
        else:
            break
    trd = TradeBot(k)
    app.exec()
