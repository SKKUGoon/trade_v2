from _workers_v2.trader import *
from main.trade_support import TradeBotUtil

from models.cms_v1 import *
from models.oms_v1 import *
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

        if co_compare is True:
            assert co_pair is not None, 'Must designate pairs for comparison'
        self.insert_model(oms_ls, cms_ls)
        tes = self.get_standard_time(self.oms)
        tes2 = self.get_standard_time(self.cms)

        self.trd = Trader(oms_ls[0], tes, oms_ls[0].params['TradeValue'], 2001, self.spec)
        self.trd.get_asset.connect(self.get_model_asset)
        self.trd.get_price.connect(self.get_rt_prc)
        self.trd.req_compare.connect(self.chk_co_asset)
        self.trd.log.connect(self.thread_log)
        self.trd.start()

        self.trd2 = Trader(cms_ls[0], tes2, cms_ls[0].params['TradeValue'], 3001, self.spec)
        self.trd2.get_asset.connect(self.get_model_asset)
        self.trd2.get_price.connect(self.get_rt_prc)
        self.trd2.req_compare.connect(self.chk_co_asset)
        self.trd2.log.connect(self.thread_log)
        self.trd2.start()

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

    def localdb_tables(self):
        # Create trade status
        self.__create_asset_status()

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

    def set_state(self, model_name, target_state, table_name='trade_state'):
        self.localdb.update_rows(
            table_name, ['trade_status'], [[target_state]], condition=f"model_name='{model_name}'"
        )
        self.log.critical(f'{model_name} state updated to {target_state}')

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

    def get_model_asset(self, signal):
        model, name, save_file_loc, exec, set_status = signal

        if exec[set_status - 1] is False:
            model.get_pred()
            asset = model.get_asset(self.spec)
            file = f'{save_file_loc}{name}_asset.pkl'
            self.save_pickle_data(asset, file)
            self.log.critical(f'Asset for {name} is generated: {asset}')

        # Change model_state
        self.set_state(name, set_status)

    def get_rt_prc(self, signal):
        screen, name, save_file_loc, exec, set_status = signal

        # Getting real time price
        if exec[set_status - 1] is False:

            self.live = LiveDBCon(self.kiwoom)
            asset_file = f'{save_file_loc}{name}_asset.pkl'
            val = self.get_pickle_data(asset_file)
            if val is not False:
                self.live.req_opt_price(val, screen)
                self.log.critical(f'Creating real-time price table for {val} at scr_num {screen}')

        # Change model_state
        self.set_state(name, set_status)

    # CO-Asset Compare.
    def chk_co_asset(self, signal):
        """
        token = (token_number, order, sell:bool, buy:bool, partial:bool)
        example)
        oms_v1: token = (1, 1, True, True, True) & asset = 'A'
        cms_v1: token = (1, 2, True, True, True) & asset = 'A'
        -> after chk_co_asset
        oms_v1: token = (1, 1, True, False, True) & asset = 'A'
        cms_v1: token = (1, 2, False, True, True) & asset = 'A'
        """
        name, token, set_status, state_loc = signal



        ...

    # def set_standard_time(self, oms_time=None, cms_time=None):
    #     if self.omse is False:
    #         assert oms_time == dict(), f'OMS model does not exist. {oms_time} should be empty.'
    #     if self.cmse is False:
    #         assert cms_time == dict(), f'CMS model does not exist. {cms_time} should be empty.'
    #
    #     if self.ymd in self.spec.maturity:
    #         self.log.critical(
    #             f'Today is {self.ymd}. No Trade on Maturity Dates. Terminating Program.'
    #         )
    #         exit()
    #     elif (self.ymd in self.spec.sat) or (self.ymd in self.spec.first_date):
    #         new_o_time, new_c_time = dict(), dict()
    #         if self.omse is not None:
    #             for model in oms_time.keys():
    #                 new_o_time[model] = {
    #                     k: v + datetime.timedelta(hours=1) for k, v in oms_time[model].items()
    #                 }
    #
    #         if self.ymd not in self.spec.sat:
    #             return new_o_time, cms_time
    #         else:
    #             if self.cmse is not None:
    #                 for model in cms_time.keys():
    #                     new_c_time[model] = {
    #                         k: v + datetime.timedelta(hours=1) for k, v in cms_time[model].items()
    #                     }
    #             return new_o_time, new_c_time
    #     else:
    #         return oms_time, cms_time




        # else:
        #     self.log.debug(f'{msg} for {model_name}')
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

    oms1 = OMS(1)
    cms1 = CMS(1)

    # t = TradeBot(k, [oms1], [cms1])
    # t = TradeBot(k, [oms1], [cms1], co_compare=True)
    # t = TradeBot(k, [], [cms1])
    t = TradeBot(k, [oms1], [cms1])
    app.exec()
