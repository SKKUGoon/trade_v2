from models.model_config import *
from main.live_db_conn import *

import math

class OMS(IramModel):
    r = None
    # OMS Starts at 08:00, day T.
    # OMS Ends at 09:30 day T.

    def __init__(self, k: Kiwoom, strategy=21):
        super().__init__(strategy)
        self.kiwoom = k
        self.spec = OrderSpec(k)
        self.strat_num = strategy
        # Log
        loc = 'C:\Data\log'
        self.log = Logger(path=loc, name='OMS_log')

        # Create OMS asset table
        self.col = {
            'days' : 'Varchar(20)',
            'strategy' : 'Varchar(20)',
            'asset' : 'Varchar(20)',
        }
        self.localdb.create_table(f'{self.strategy}', variables=self.col)

    def get_pred(self, table='omsr'):  # TODO: get table name from strategy itself
        """
        Starts at 08:30
        Must be end at 08:40
        """

        t = datetime.datetime.now().strftime('%Y%m%d')
        self.r = dict()
        for i in range(self.max_retry):
            try:
                col = self.iramdb.get_column_list(table.lower())
                res = self.iramdb.select_db(target_column=col,
                                            target_table=table,
                                            condition=f"days >= {t}")
                self._check_input(res)
                for key, val in zip(col, res[0]):
                    self.r[key] = val
                self.log.debug(f"Trade Prediction for {self.strategy} fetched")
            except RetrieveNoneError:
                self.log.warning('Get_pred function returned None.')
                self.reconn_server()
            else:
                break
        else:
            self.r = None  # If there is no prediction: self.r is None

    @property
    def oms_days(self):
        return self.r['days']

    @property
    def oms_asset(self):
        return self.r['code'].split('_')[0]  # TODO: Unify Database

    @property
    def oms_version(self):
        return self.r['version']

    @property
    def oms_prediction(self):
        return self.r['pre_corrected']  # TODO: Unify Database

    def get_asset(self):
        """
        Gets real closing price at 15:30
            - Fetch it from the
        """
        current = self.spec.tick_price_base()
        asset_call, asset_put = self.spec.gen_option_code(current)
        prediction = self.oms_asset.lower()

        if prediction == 'call' :
            self._save_asset_local(asset_call)
            self.log.debug(f'Asset is {asset_call}. Uploaded to local DB')
            return asset_call
        elif prediction == 'put' :
            self._save_asset_local(asset_put)
            self.log.debug(f'Asset is {asset_put}. Uploaded to local DB')
            return asset_put
        else:
            # Terminate. No Transaction
            asset = 'N/A'
            self.log.warning(f"Prediction value is {prediction}. Terminating Process")
            return False

    def _save_asset_local(self, asset):
        # [days, time, pred, asset_code]
        start = datetime.datetime.now().strftime('%Y%m%d')
        self.localdb.insert_rows(f'{self.strategy}',
                                 list(self.col.keys()),
                                 [[start, self.strategy, asset]])

    def _buy_order(self, test=False):
        # After sleep, get current price data
        col = self.localdb.get_column_list('RT_Option')
        val = self.localdb.select_db(col,
                                     target_table='RT_Option')

        price = float(val[0][col.index('p_buy')])
        quantity = self.total_value / (price * 250000)

        return price, math.floor(quantity)

    def get_asset_local(self, t):
        """
        Target Assets are stored in Local DB
        Function return asset as string value
        """
        for _ in range(self.max_retry):
            try:
                asset = self.localdb.select_db(target_column=self.col,
                                               target_table=self.strategy,
                                               condition1=f'days >= {t}')[0]
                asset = asset[list(self.col.keys()).index('asset')]
            except IndexError:
                self.log.warning(f"No prediction input. Retrying")
                time.sleep(5)
            else:
                break
        else:
            self.log.critical(
                f"No prediction input after {self.max_retry} retrying attempts."
            )
            return None
        return asset

    def order_spec_oms(self, tick=0):
        start = datetime.datetime.now().strftime('%Y%m%d')

        asset = self.get_asset_local(start)
        if asset is None:
            self.log.critical(
                f'Shut down {self.strategy} for {start}. CAUSE: No prediction'
            )
            return None

        set_price, set_quantity = self._buy_order()

        # Plus extra alphas for price
        set_price = set_price + tick

        # Make Order Sheet
        self.oms_count = 1
        self.screen_oms = str(self.strat_num * 100)

        order_oms = {'rq_name' : f'oms{self.oms_count}',
            'screen_num' : self.screen_oms,
            'account' : self.kiwoom.account_num[1],
            'code' : asset,
            'order_type' : 1,  # 1: New, 2: Refract, 3: Cancel
            'buy_sell' : 2,  # Selling, Buying
            'trade_type' : 1,  # Designated Price
            'quantity' : set_quantity,
            'price' : set_price,
            'order_num' : ""}

        return order_oms

    def sendit(self):
        order = self.order_spec_oms()
        self.spec.send_order_fo(**order)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    k = Kiwoom.instance()
    k.connect()

    c = OMS(k)
    c.get_asset_local('20201221')