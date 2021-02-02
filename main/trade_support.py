from _workers_v2.trader import *
from _code.trade_state import state2 as tradestate

from models.oms_old_db import *

import time


class TradeBotUtil:
    state = tradestate
    new_start = True
    ymd = datetime.datetime.now().strftime('%Y%m%d')

    def __init__(self):
        """
        This class has utility functions regarding TradeBot class
            such as handling high premium, getting floor values, adjusting price
            and get real-time price.
        Also this class contains some necessary parameters
        """

        # Log
        self.q = Queue()
        loc = 'C:\Data\log'
        self.log = Logger(path=loc, name='Trade_log', queue=self.q)
        self.log.critical('Trade Starting')

    def set_restart(self, current_state):
        if current_state != 0:
            self.new_start = False

    # Utility functions.
    @staticmethod
    def chk_premium_prc(price: float, decimal=2, standard=5):
        """
        If the premium exceeds 10 point,
            the minimum unit changes from 0.01 to 0.05
        """
        if price >= 10:
            if price * (10 ** (decimal)) % 5 == 0:
                return price
            else:
                price_d = price * (10 ** decimal)
                return (price_d + (standard - (price_d % standard))) * 10 ** (-decimal)
        else:
            return price

    @staticmethod
    def get_floor(value, decimal=2):
        # Math Floor gives too much error.
        return (value * (10 ** decimal) // 1) * (10 ** -decimal)

    @staticmethod
    def get_adjust_prc(price, c: int, base=0.01):
        return price + (c * base)

    @staticmethod
    def get_rt_price(asset, buysell, local:LocalDBMethods2,
                     orderer:OrderSpec, logger:Logger, from_table='RT_Option', timeout=30):
        col = local.get_column_list(from_table)
        ts = time.time()
        while time.time() - ts <= timeout:
            try:
                val = local.select_db(
                    target_column=col,
                    target_table=from_table,
                    condition1=f"code = '{asset}'")
                price = float(val[0][col.index(buysell)])
                return price
            except Exception:
                continue
            else:
                break
        logger.debug('No Live Price input, Plugging it latest price instead')
        price = orderer.tick_price_fo(asset)
        return price

    @staticmethod
    def save_pickle_data(data, filename: str):
        with open(filename, 'wb') as file:
            pickle.dump(data, file)

    @staticmethod
    def get_pickle_data(filename: str):
        with open(filename, 'rb') as file:
            return pickle.load(file)

    @staticmethod
    def get_standard_time(original:Dict, asset_slack=5, from_format='%H:%M:%S'):
        res = dict()
        for model in original.keys():
            ts, te = list(map(lambda x: datetime.datetime.strptime(x, from_format),
                              [original[model]['TradeStartTime'], original[model]['ClearTime']]))
            res['get_asset'] = ts - datetime.timedelta(minutes=asset_slack)
            res['trade_start'], res['trade_end'] = ts, te
        return res
