from PyQt5.QtWidgets import QApplication

from util.UTIL_dbms import *

from main.KWDERIV_order_spec import OrderSpec
from main.KW_kiwoom_main import Kiwoom

import datetime
import sys

assert sys.version_info >= (3, 6), f'python version should be 3.6 or higher'

class TradeResultRecord:
    """
    Execute every 18:00:00
    """
    fileloc = r'D:\trade_db\trade_result.db'
    ymd_dt = datetime.datetime.now()
    ymd = ymd_dt.strftime('%Y%m%d')
    ymd_dt = datetime.datetime(2021, 5, 15)
    ymd = '20210515'

    def __init__(self, k:Kiwoom):
        self.k = k
        self.ord = OrderSpec.instance(k)
        self.local = LocalDBMethods2(self.fileloc)
        self.create_table()
        self.create_table(True)

    def create_table(self, past=False):
        current = {
            'date' : 'Varchar(20)',
            'asset': 'Varchar(20)',
            'price': 'Float(3)',
            'quantity': 'Double',
            'value': 'Double',
            'money': 'Double'
        }
        name = 'overnight_asset'
        if past is True:
            current['processed'] = 'Varchar(20)'
            name = 'traded_asset'
        self.local.create_table(
            table_name=name,
            variables=current
        )

    def get_asset(self):
        asset_cur, asset_past = self.ord.get_fo_deposit_info(
            self.k.account_num[0]
        )
        money = self.ord.get_fo_margin_info(
            self.k.account_num[0]
        )

        return asset_cur, asset_past, money

    def _create_log_row(self, data:dict, money, overnight:bool):
        prc = int(float(data['tv'])) / int(float(data['quantity']))
        row = [
            (self.ymd_dt + overnight * datetime.timedelta(days=1)).strftime('%Y%m%d'),
            data['asset_code'],
            float(prc),
            int(float(data['quantity'])),
            int(float(data['tv'])),
            int(float(money))
        ]
        if overnight is False:
            row.append('processed')
        return row

    def _update_overnight_asset(self, cur:str, pas:str):
        current, past, _ = self.get_asset()




        res = self.local.select_db(
            target_column=['*'],
            target_table='overnight_asset'
        )
        col = self.local.get_column_list('overnight_asset')
        for obs in res:
            if obs[col.index('date')] == self.ymd:
                if obs[col.index('asset')] in [p['asset_code'] for p in past]:
                    proc = 'processed'
                else:
                    proc = 'processed'
                obs = list(obs)
                obs.append(proc)
                self.local.insert_rows(
                    pas,
                    col_=self.local.get_column_list(pas),
                    rows_=[obs]
                )

        # self.local.delete_rows(cur, f"date = '{self.ymd}'")

    def log_trade(self, current_table='overnight_asset', past_table='traded_asset'):
        self._update_overnight_asset(cur=current_table,
                                     pas=past_table)
        current, past, money_left = self.get_asset()

        for asset_info in current:
            row = self._create_log_row(asset_info, money_left, True)
            self.local.insert_rows(
                current_table,
                col_=self.local.get_column_list(current_table),
                rows_=[row]
            )

        for asset_info in past:
            row = self._create_log_row(asset_info, money_left, False)
            self.local.insert_rows(
                past_table,
                col_=self.local.get_column_list(past_table),
                rows_=[row]
            )





if __name__ == '__main__':
    app = QApplication(sys.argv)
    k = Kiwoom.instance()
    k.connect()

    test = TradeResultRecord(k)
    test.log_trade()
