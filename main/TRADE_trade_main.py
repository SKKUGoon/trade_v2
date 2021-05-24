from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from workers.THREAD_trader import *

from util.UTIL_dbms import *
from util.UTIL_asset_code import *

from main.TRADE_trade_back import TradeBotUtil
from main.KWDERIV_order_spec import OrderSpec
from main.KWDERIV_live_db_conn import LiveDBCon
from main.KW_kiwoom_main import Kiwoom

from workers.THREAD_tts import TwoToSeven
from workers.THREAD_cms_ import CMS
from workers.THREAD_cmsext import CMSExt

import time
import sys

assert sys.version_info >= (3, 6), f'python version should be 3.6 or higher'


class TradeBot(TradeBotUtil):
    """
    Execute this Bot at 09:01:00
    """
    def __init__(self, k:Kiwoom):
        print('This Module is to purchase 2 ~ 7 Put Option.')
        # Necessary Modules
        super().__init__()

        # DB Connect
        loc = r'D:\trade_db\local_trade._db'
        self.localdb = LocalDBMethods2(loc)
        self.localdb.conn.execute("PRAGMA journal_mode=WAL")
        self.prep_db()

        self.kiwoom = k
        self.spec = OrderSpec.instance(k)
        self.live = LiveDBCon.instance(k)
        self.morning = self._morn_status()
        self.maturity = self._maturity_status()

        # Start Thread
        self.create_threadpool()
        self.timer_start_thread()

        self.iram = MySQLDBMethod(None, 'main')

    def prep_db(self):
        prep_del = ['RT_Option', 'RT_TR_S', 'RT_TR_C', 'RT_TR_E']
        for table in prep_del:
            self.localdb.delete_table(table)

    def _time_until(self, target:datetime.datetime, unit='msec'):
        called = datetime.datetime.strptime(
            datetime.datetime.now().strftime(self.time_format),
            self.time_format
        )

        until = (target - called).seconds
        if (target - called).days < 0:
            until = 0

        if unit == 'msec':
            return until * 1000
        else:
            return until

    def _maturity_status(self):
        mat = get_exception_date('MaturityDay')
        for days in mat:
            if self.ymd == days:
                return True
        return False

    def _morn_status(self):
        if self.hms <= '120000':
            return True
        else:
            return False

    # Thread Related
    def create_threadpool(self):
        self.log.critical('ThreadPool Generated')
        threads = QThreadPool.globalInstance().maxThreadCount()
        self.pool = QThreadPool.globalInstance()

    def _thread_tasks_tts(self):
        self.log.critical('TwoToSeven Thread Starting')
        tts = TwoToSeven(orderspec=self.spec,
                         live=self.live,
                         morning=self.morning,
                         cmsext=False)
        self.pool.start(tts)

    def _thread_tasks_cms(self):
        self.log.critical('CMS Thread Starting')
        cms = CMS(orderspec=self.spec,
                  morning=self.morning,
                  maturity=self.maturity,
                  live=self.live)

        self.pool.start(cms)

    def _thread_tasks_cmsext(self):
        self.log.critical('CMSExt Thread Starting')
        cmsext = CMSExt(orderspec=self.spec,
                        live=self.live,
                        morning=self.morning,
                        cmsext=False)
        self.pool.start(cmsext)

    def _get_target_time(self):
        # Get Starting Time of the PROGRAM.
        fb = get_exception_date('1stBusinessDay')
        sat = get_exception_date('SAT')

        if self.ymd in sat:
            target = {
                'tts': datetime.datetime.strptime('100020', self.time_format),
                'cms': datetime.datetime.strptime('155000', self.time_format),
                'cmsext': datetime.datetime.strptime('094000', self.time_format)
            }
        elif self.ymd in fb:
            target = {
                'tts': datetime.datetime.strptime('100020', self.time_format),
                'cms': datetime.datetime.strptime('145000', self.time_format),
                'cmsext': datetime.datetime.strptime('094000', self.time_format)
            }
        else:
            target = {
                'tts': datetime.datetime.strptime('090020', self.time_format),
                'cms': datetime.datetime.strptime('145000', self.time_format),  # TODO Change
                'cmsext': datetime.datetime.strptime('084000', self.time_format)
            }
        return target

    def timer_start_thread(self):
        tgt_time = self._get_target_time()

        QTimer.singleShot(
            self._time_until(tgt_time['tts']),  # Change here to test
            self._thread_tasks_tts
        )
        QTimer.singleShot(
            self._time_until(tgt_time['cms']),
            self._thread_tasks_cms
        )
        QTimer.singleShot(
            self._time_until(tgt_time['cmsext']),
            self._thread_tasks_cmsext
        )


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
