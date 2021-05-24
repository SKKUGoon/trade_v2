import configparser as cp
import time

from code_.KW_status import TRName
from util.UTIL_asset_code import *
from main.KW_kiwoom_main import *

from PyQt5.QtWidgets import QMainWindow


class OrderSpec(QMainWindow):
    """
    OrderSpec 1 class handles functions associated with DB connection.
    """
    __instance = None
    cfg = cp.ConfigParser()
    cfg.read(r'./main/config.ini')

    opt_mp = 250000  # unit price for each premium
    opt_tick = 0.01

    @classmethod
    def __get_instance(cls):
        return cls.__instance

    @classmethod
    def instance(cls, *args, **kwargs):
        cls.__instance = cls(*args, **kwargs)
        cls.instance = cls.__get_instance
        return cls.__instance

    def __init__(self, k):
        # Kiwoom Api Connection

        super().__init__()
        self.k = k

        # MySQL connection
        self.iramdb = MySQLDBMethod(None, 'main')

        # Exception Dates
        self.maturity = self._exception_date('MaturityDay')
        self.sat = self._exception_date('SAT')
        self.first_date = self._exception_date('1stBusinessDay')

        # Config
        self.account = self.k.account_num

    def req_kw(self, tr_code, **kwargs):
        if tr_code == 'OPTKWFID':
            return None  # Not implemented
        for k, v in kwargs.items():
            self.k.set_input_value(k, v)
        tr_name = getattr(TRName, tr_code)
        self.k._comm_rq_data(tr_name, tr_code, 0, "0101")
        return getattr(self.k, tr_code)

    def get_deposit_info(self, account, target_var="D+2추정예수금"):
        res = self.req_kw('OPW00004', **{'계좌번호': account})
        if target_var in getattr(TRKeys, 'OPW00004').get('싱글데이터'):
            ans = int(res.get('싱글데이터').get(target_var).replace(",", ""))
        elif target_var in getattr(TRKeys, 'OPW00004').get('멀티데이터'):
            for md in res.get('멀티데이터'):
                if target_var in md:
                    return md[target_var]
        else:
            raise OrderSpecError(f'{target_var} not in data list')

    def get_fo_margin_info(self, account):
        res = self.req_kw('OPW20010', **{'계좌번호': account})
        res = res['싱글데이터']
        return int(res['주문가능현금'])


    def get_fo_deposit_info(self, account):
        col = {
            '계좌번호': 'account_num',
            '종목코드': 'asset_code',
            '보유수량': 'quantity',
            '총매입가': 'tv',
            '예수금': 'account_value',
        }
        res = self.req_kw('OPT50027', **{'계좌번호': account})
        res = res.get('멀티데이터')
        for asset_info in res:
            for k, v in asset_info.items():
                asset_info[k] = self.make_pretty(v)
        have = list()  # Asset have
        had = list()  # Asset had
        for asset in res:
            if int(asset['보유수량']) != 0:
                have.append(
                    dict((col[key], value) for (key, value) in asset.items())
                )
            else:
                had.append(
                    dict((col[key], value) for (key, value) in asset.items())
                )
        return have, had

    def _exception_date(self, type_: str, table='ftsdc') -> set:
        """
        All the Exceptions are inside ftsdc table
        :param type_: includes 3 types
            - Maturity day: 'MaturityDay'
            - SAT : 'SAT'
            - First Business Day : '1stBusinessDay'
        :return: as DataFrame
        """
        start = datetime.datetime.now()
        col = self.iramdb.get_column_list(table)
        res = self.iramdb.select_db(target_column=col,
                                    target_table=table,
                                    condition=f"type='{type_}'")
        res = set(
            map(
                lambda x: x[1] if x[1][:6] >= start.strftime('%Y%m') else 0,
                res
            ))  # Get Present year ~ Future dates only
        res = list(res)
        res.remove(0)
        return sorted(res)

    @staticmethod
    def make_pretty(val):
        val = val.replace(' ', '')
        val = val.lstrip('-')
        val = val.lstrip('+')
        return val

    def minute_price_base(self, code='201', freq='1') -> float:
        params = {
            "업종코드": code,
            "틱범위": freq,
        }
        dat = self.req_kw(tr_code="opt20005", **params)
        d = dat['멀티데이터'][0]  # Use the most recent data
        res = dict()
        for k, v in d.items():
            res[k] = self.make_pretty(v)
        price = res['현재가']
        return dat

    def minute_price_fo(self, code, freq='1') -> Dict:
        params = {
            "종목코드": code,
            "시간단위": freq,
        }
        while True:
            try:
                dat = self.req_kw(tr_code="opt50067", **params)
                price = float(self.make_pretty(dat['멀티데이터'][0]['현재가']))
            except Exception:
                time.sleep(1)
                continue
            else:
                break

        return dat

    def get_tgtmin_price_fo(self, code, target_min):
        res = self.minute_price_fo(code)
        for _ in res['멀티데이터']:
            if self.make_pretty(_['체결시간'])[-6:] == target_min:
                return self.make_pretty(_['시가'])

    def tick_price_base(self, code='201', freq='1') -> float:
        params = {
            "업종코드" : code,
            "틱범위" : freq
        }
        while True:
            try:
                dat = self.req_kw(tr_code="opt20004", **params)
                price = int(self.make_pretty(dat['멀티데이터'][0]['현재가'])) / 100
            except Exception as e:
                print(e)
                print('Price information yet to arrive. Retrying')
                time.sleep(1)
                continue
            else:
                break
        return price

    def tick_price_fo(self, code, freq='1') -> float:
        params = {
            "종목코드" : code,
            "시간단위" : freq
        }

        while True:
            try:
                dat = self.req_kw(tr_code="opt50066", **params)
                price = float(self.make_pretty(dat['멀티데이터'][0]['현재가']))
            except Exception:
                print("Price information yet to arrive. Retrying")
                time.sleep(1)
                continue
            else:
                break
        return price

    def gen_option_code(self, index, day=datetime.datetime.now()):
        today = day.strftime('%Y%m%d')
        # If Maturity Date is passed, return next month
        # If Maturity Date is not passed, return this month
        if today < self.maturity[0]:
            ba_cond = 'before'
        else:
            ba_cond = 'after'
        opt_call = asset_code_gen(index=index,
                                  type_='call_option',
                                  date_info=day,
                                  bfaf=ba_cond)
        opt_pull = asset_code_gen(index=index,
                                  type_='put_option',
                                  date_info=day,
                                  bfaf=ba_cond)
        return opt_call, opt_pull

    def create_order_stock(self, rq_name, screen_num, account, order_type,
                           code, quantity, price, trade_type, original_order_num=""):
        order_spec = {
            'rq_name': rq_name,
            'screen_num': screen_num,
            'account': account,
            'order_type': order_type,
            'code': code,
            'quantity': quantity,
            'price': price,
            'trade_type': trade_type,
            'original_order_num': original_order_num
        }

        return order_spec

    def create_order_option(self, rq_name, screen_num, account, code, order_type,
                            buy_sell, trade_type, quantity, price, order_num,
                            time=None, signal=None):
        order_spec = {
            'rq_name': rq_name,
            'screen_num': screen_num,
            'account': account,
            'code': code,
            'order_type': order_type,
            'buy_sell': buy_sell,
            'trade_type': trade_type,
            'quantity': quantity,
            'price': price,
            'order_num': order_num
        }
        return order_spec

    def send_order(self, rq_name, screen_num, account, order_type,
                   code, quantity, price, trade_type, original_order_num="",
                   time=None, signal=None):

        self.k.send_order(rq_name, screen_num, account, order_type,
                          code, quantity, price, trade_type, original_order_num)

        # return getattr(self.k, 'order_response')

    def send_order_fo(self, rq_name, screen_num, account, code, order_type,
                      buy_sell, trade_type, quantity, price, order_num,
                      time=None, signal=None):
        self.k.send_order_fo(rq_name, screen_num, account, code, order_type,
                             buy_sell, trade_type, quantity, price, order_num)

        # return getattr(self.k, 'order_response')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    k = Kiwoom.instance()
    k.connect()
    ord = OrderSpec.instance(k)
    b = ord.tick_price_fo('201R6425')
    c = ord.minute_price_fo('201R6425')
    d = ord.minute_price_base()
    ord.get_fo_deposit_info(k.account_num[0])
    ord.get_tgtmin_price_fo('201R6425', '150000')
