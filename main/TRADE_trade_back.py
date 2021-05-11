from workers.THREAD_trader import *
import time


class TradeBotUtil:
    new_start = True
    date_format = '%Y%m%d'
    time_format = '%H%M%S'
    ymd = datetime.datetime.now().strftime(date_format)
    hms = datetime.datetime.now().strftime(time_format)


    def __init__(self):
        """
        This class has utility functions regarding TradeBot class
            such as handling high premium, getting floor values, adjusting price
            and get real-time price.
        Also this class contains some necessary parameters
        """
        # Log
        loc = r'D:\trade_db\log'
        self.log = Logger(loc, 'Trade_log')
        self.log.critical('Trade Starting')

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


