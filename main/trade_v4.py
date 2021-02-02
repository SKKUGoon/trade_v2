from _workers_v2.re_tr_workers_v2 import *
from main.trade_support import TradeBotUtil

from models.cms import *
from models.oms_old_db import *
# from models.oms import *

from typing import List
from queue import Queue
import pickle
import time
import copy

assert sys.version_info >= (3, 6), f'python version should be 3.6 or higher'


class TradeBot(TradeBotUtil):
    oms, cms, total = dict(), dict(), dict()
    omse, cmse = True, True
    oms_screen, cms_screen, coms_screen = 2000, 3000, 1000

    def __init__(self, k, oms_ls: List[OMS], cms_ls: List[CMS], co_compare=False, co_pair=None):
        print(f'Trading Bot running on {threading.currentThread().getName()}')
        # Necessary Modules
        super().__init__()
        self.kiwoom = k
        self.spec = OrderSpec(k)

        # DB Connectivity
        loc = r'C:\Data\local_trade._db'
        self.localdb = LocalDBMethods2(loc)
        self.localdb.conn.execute("PRAGMA journal_mode=WAL")
        self.localdb_tables()

        self.set_restart(self.start_status)

        if co_compare is True:
            assert co_pair is not None, 'Must designate pairs for comparison'
        self.insert_model(oms_ls, cms_ls)
        tes = self.get_standard_time(self.oms)

        self.trd = Trader(oms_ls[0], tes, None)
        self.trd.start()

    def thread_log(self, signal: tuple):
        msg, level = signal
        if level.lower() == 'debug':
            self.log.debug(msg)
        elif level.lower() == 'critical':
            self.log.critical(msg)
        elif level.lower() == 'warning':
            self.log.warning(msg)
        elif level.lower() == 'error':
            self.log.error(msg)

    def bool_param_check(self, compare_arg):
        if any((self.omse, self.cmse)) is False:
            self.log.critical('No models were inserted. Terminating')
            exit()

        elif all((self.omse, self.cmse)) is False and compare_arg is True:
            self.log.critical('Single Model were inserted ')

    def localdb_tables(self):
        # Create trade status
        self.__create_trade_status()
        self.__create_asset_status()
        self.start_status = self.localdb.select_db(
            target_column=['trade_status'], target_table='trade_state')[0][0]

    def __create_trade_status(self, table_name='trade_state'):
        param = {'trade_status': 'int'}
        self.localdb.create_table(
            table_name=table_name, variables=param
        )
        count = self.localdb.count_rows(table_name)
        if count == 0:
            self.localdb.insert_rows(
                table_name,
                col_=list(param.keys()),
                rows_=[[self.state['Input_Models']]])

    def __create_asset_status(self, table_name='asset_state'):
        param = {
            'days': 'Varchar(20)',
            'screen': 'Varchar(20)',
            'model': 'Varchar(20)',
            'account_num': 'Varchar(20)',
            'asset_code': 'Varchar(20)',
            'quantity': 'Varchar(20)',
            'tv': 'Varchar(20)',
            'from_status': 'INT'
        }
        self.localdb.create_table(table_name=table_name,
                                  variables=param)

    def go_to_status(self, state):
        self.localdb.update_rows('trade_state', ['trade_status'], [[state]])

    def insert_model(self, oms, cms):
        if len(oms) == 0:
            self.omse = False

        if len(cms) == 0:
            self.cmse = False

        for o in oms:
            assert isinstance(o, OMS)
            self.oms[o.strategy] = o.params
            self.oms[o.strategy]['model'] = o

        for c in cms:
            assert isinstance(c, CMS)
            self.cms[c.strategy] = c.params
            self.cms[c.strategy]['model'] = c

        self.total = {'oms': self.oms, 'cms2': self.cms}

    def set_standard_time(self, oms_time=None, cms_time=None):
        if self.omse is False:
            assert oms_time == dict(), f'OMS model does not exist. {oms_time} should be empty.'
        if self.cmse is False:
            assert cms_time == dict(), f'CMS model does not exist. {cms_time} should be empty.'

        if self.ymd in self.spec.maturity:
            self.log.critical(
                f'Today is {self.ymd}. No Trade on Maturity Dates. Terminating Program.'
            )
            exit()
        elif (self.ymd in self.spec.sat) or (self.ymd in self.spec.first_date):
            new_o_time, new_c_time = dict(), dict()
            if self.omse is not None:
                for model in oms_time.keys():
                    new_o_time[model] = {
                        k: v + datetime.timedelta(hours=1) for k, v in oms_time[model].items()
                    }

            if self.ymd not in self.spec.sat:
                return new_o_time, cms_time
            else:
                if self.cmse is not None:
                    for model in cms_time.keys():
                        new_c_time[model] = {
                            k: v + datetime.timedelta(hours=1) for k, v in cms_time[model].items()
                        }
                return new_o_time, new_c_time
        else:
            return oms_time, cms_time

    # CO-Asset Compare.
    def chk_co_asset(self, signal: str):
        ...

    def get_rt_prc(self, signal: str):
        ...
        # msg, model_name, key_name, init = signal
        # if self.executed[key_name] is True:
        #     self.log.debug('Already executed this function')
        # else:
        #     self.log.debug(f'{msg} for {model_name}')
        #     self.executed[key_name] = True
        #     self.live = LiveDBCon(self.kiwoom)
        #     if int(init) == self.state['CO_Diff_OMS_Live_Price']:
        #         asset = self._open_pickle(f'./_pickles2/{model_name}_buy.pkl')
        #         assert model_name in self.oms.keys()
        #         for a in asset:
        #             self.live.req_opt_price(a, self.oms_screen)
        #             self.log.debug(f'{msg} for {model_name}. Asset : {asset}')
        #         # Afterwards
        #         if self.cmse:
        #             self.go_to_status(self.state['CO_Diff_CMS1_Live_Price'])
        #         else:
        #             self.go_to_status(self.state['CO_Diff_OMS_Buy'])
        #
        #     elif int(init) == self.state['CO_Diff_CMS1_Live_Price']:
        #         asset = self._open_pickle(f'./_pickles2/{model_name}_sell.pkl')
        #         assert model_name in self.cms.keys()
        #         for a in asset:
        #             self.live.req_opt_price(a, self.cms_screen)
        #             self.log.debug(f'{msg} for {model_name}. Asset : {asset}')
        #
        #         self.go_to_status(self.state['CO_Diff_CMS_Sell'])
        #
        #     elif int(init) == self.state['CO_Same_Live_Price']:
        #         # When it's same, we get oms_based information
        #         asset = self._open_pickle(f'./_pickles2/{model_name}_buy.pkl')
        #         for a in asset:
        #             self.live.req_opt_price(asset, self.coms_screen)
        #             self.log.debug(f'{msg} for {model_name}. Asset : {asset}')
        #
        #         self.go_to_status(self.state['CO_Same_CMS_Sell'])
        #
        #     else:
        #         self.log.error(f"Wrong signal given: signal: {signal}")
        #         exit()

    def shutdown_trade(self):
        ...
        exit()


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

    oms1 = OMS(k)
    cms1 = CMS(k)

    # t = TradeBot(k, [oms1], [cms1])
    # t = TradeBot(k, [oms1], [cms1], co_compare=True)
    # t = TradeBot(k, [], [cms1])
    t = TradeBot(k, [oms1], [cms1])
    app.exec()
