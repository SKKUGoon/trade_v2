from _util.errors import *
from _util._log import *
from _util.dbms import *

import pandas as pd

import configparser as cp
import datetime
import time


# <Old Category ID>
# 10 : TSF_201_OLS_long
# 20 : OMS_opt_long
# 7 : TSF_201_GLS_long
# 21 : OMS_opt_long_v2
# 13 : TSF_201_v2_long
# 23 : CMS_v1
# etc

# <New Category ID(suggestion)>
# 1xx series : TSFs
#   - 11 : TSF version 1
# 2xx series : OMSs
#   - 21 : OMS version 1
# 3xx series : CMSs
#   - 31 : CMS version 1
#   - 311 : CMS version 11
#   - 321 : CMS version 21


class IramModel:
    strat_name = {
        11 : 'TSF_v1', 21 : 'OMS_opt_long_v2', 31 : 'CMS_v1',  # TODO Unify Name
        12 : 'TSF_v2', 22 : 'OMS_v2', 32 : 'CMS_v2'
    }
    # DataBase Access Parameters
    cfg = cp.ConfigParser()
    cfg.read('config.ini')  # config file address
    #cfg.read(r'C:\Users\iram_SI\PycharmProjects\TradingProgram\config.ini')
    local_db_loc = r'C:\Data\local_trade._db'

    max_retry = 60
    status = None

    def __init__(self, strategy:int):
        # DataBase Connection
        self.localdb = LocalDBMethods2(self.local_db_loc)
        self.localdb.conn.execute("PRAGMA journal_mode=WAL")
        self.iramdb = MySQLDBMethod(self.cfg, 'main')
        self.strategy = self.strat_name[strategy]

        # Log
        loc = 'C:\Data\log'
        self.log = Logger(path=loc, name='Model_log')

        self.params = self.trade_param

    def _check_input(self, input):
        if input is None:
            raise RetrieveNoneError
        else:
            pass

    def _set_strat_num(self, val):
        self.status = val
        return self.status

    def reconn_server(self, delay=1):
        """
        Retrying after sleeping for {delay} second
        """
        time.sleep(delay)
        t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        self.log.warning(f"{t} Iram Server Conn fail. Retrying")
        self.iramdb = MySQLDBMethod(self.cfg, 'main')

    def reconn_local(self, delay=1):
        """
        Retrying after sleeping for 1 second
        """
        time.sleep(delay)
        t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        self.log.warning(f"{t} Local SQL Conn fail. Retrying")
        self.localdb = LocalDBMethods2(self.local_db_loc)

    @property
    def trade_param(self) -> dict:
        """
        Record trading parameters into dictionary
        """
        for i in range(self.max_retry):
            try:
                col = self.iramdb.get_column_list(table_name='v_stp')
                res = self.iramdb.select_db(col,
                                            target_table='v_stp',
                                            condition=f"fullname = '{self.strategy}'")  # Designate Strategy number
                self.log.debug(f"{datetime.datetime.now()} Trade Parameters for {self.strategy} fetched")
            except AttributeError:
                self.log.warning(f"{datetime.datetime.now()} Reconnecting to server")
                self.reconn_server()
            else:
                break
        else:
            self.log.critical(f"All {self.max_retry} ATTEMPTS FAILED.")

        res = pd.DataFrame(res, columns=col)

        self.params = dict()
        for type_, value in zip(res.ParameterType, res.ParameterValue):
            self.params[type_] = value
        return self.params

    @property
    def trade_start(self):
        k = 'TradeStartTime'
        if k in self.params.keys():
            return self.params[k]

    @property
    def prg_terminate(self):
        k = 'TruncTime'
        if k in self.params.keys():
            return self.params[k]

    @property
    def loss_cut(self):
        k = 'Losscut'
        if k in self.params.keys():
            return int(self.params[k])

    @property
    def trade_end(self):
        k = 'ClearTime'
        if k in self.params.keys():
            return self.params[k]

    @property
    def total_value(self):
        k = 'TradeValue'
        if k in self.params.keys():
            return int(self.params[k])

    @property
    def time_limit(self):
        k = 'TimeLimit'
        if k in self.params.keys():
            return int(self.params[k])

    @property
    def overnight(self):
        k = 'Overnight'
        if k in self.params.keys():
            return int(self.params[k])

if __name__ == '__main__':
    cfg = cp.ConfigParser()
    cfg.read('config.ini')

    mysql = MySQLDBMethod(cfg, 'main', test=False)
    test = IramModel('CMS_v1')
