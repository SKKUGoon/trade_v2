from models.model_config import *
from main.live_db_conn import *

import math

class CMS(IramModel):
    # CMS Starts at 15:00, day T.
    # CMS Ends at 09:00 day T+1.
    def __init__(self, k: Kiwoom, strategy=31):
        super().__init__(strategy)
        self.kiwoom = k
        self.live = None
        self.spec = OrderSpec(k)
        self.strat_num = strategy

        # Log
        loc = 'C:\Data\log' #
        self.log = Logger(path=loc, name='CMS_log')

        # Create CMS asset table
        self.col = {
            'days' : 'Varchar(20)',
            'strategy' : 'Varchar(20)',
            'asset' : 'Varchar(20)',
        }
        self.localdb.create_table(f'{self.strategy}', variables=self.col)

    def get_pred(self, table='cmsr'):
        """
        Starts at 15:20
        Must be end at 15:30
        """
        t = datetime.datetime.now().strftime('%Y%m%d')
        self.r = dict()
        for i in range(self.max_retry):
            try:
                col = self.iramdb.get_column_list(table.lower())
                res = self.iramdb.select_db(
                    target_column=col,
                    target_table=table,
                    condition=f"days >= {t} and version = 'v2'"
                )
                self._check_input(res)
                for key, val in zip(col, res[0]):
                    self.r[key] = val
                self.log.debug(f"Trade Prediction for {self.strategy} fetched")
            except (RetrieveNoneError, IndexError):
                self.log.warning('Get_pred function returned None.')
                self.reconn_server()
            else:
                break
        else:
            self.r = None

    @property
    def cms_days(self):
        return self.r['days']

    @property
    def cms_asset(self):
        return self.r['asset']

    @property
    def cms_version(self):
        return self.r['version']

    @property
    def cms_prediction(self):
        return self.r['prediction']

    def gen_asset(self):
        current = self.spec.tick_price_base()
        asset_call, asset_put = self.spec.gen_option_code(current)
        prediction = self.cms_asset.lower()
        action = self.cms_prediction

        if prediction == 'call' and action == 1:
            self._save_asset_local(asset_call)
            self.log.debug(f'Asset is {asset_call}. Uploaded to local DB')
            return asset_call
        elif prediction == 'put' and action == 1:
            self._save_asset_local(asset_put)
            self.log.debug(f'Asset is {asset_put}. Uploaded to local DB')
            return asset_put
        else:
            # Terminate. No Transaction
            if prediction == 'call':
                a = asset_call
            else:
                a = asset_put
            self.log.warning(f"Asset code: {a} Action: {action}. Terminating Process")
            return False

    def gen_asset_price(self, asset, scr_num, cols, test=False):
        if test is True:
            self.live = LiveDBCon(self.kiwoom, termination=datetime.timedelta(minutes=2))
        else:
            self.live = LiveDBCon(self.kiwoom)
        self.live.req_opt_price(asset, scr_num, cols)

    def _save_asset_local(self, asset):
        # [days, time, pred, asset_code]
        start = datetime.datetime.now().strftime('%Y%m%d')
        self.localdb.insert_rows(f'{self.strategy}',
                                 list(self.col.keys()),
                                 [[start, self.strategy, asset]])

    def _buy_order(self):
        # After sleep, get current price data
        col = self.localdb.get_column_list('RT_Option')
        val = self.localdb.select_db(col,
                                     target_table='RT_Option',
                                     condition2='ORDER BY server_time DESC LIMIT 1')

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
                f"No prediction input after {self.max_retry} retrying attempts"
            )
            return None
        return asset

    def order_spec_cms(self, tick=0):
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
        self.cms_count = 1
        self.screen_cms = str(self.strat_num * 100)

        order_cms = self.spec.create_order_option(
            rq_name=f'cms{self.cms_count}',
            screen_num=self.screen_cms,
            account=self.kiwoom.account_num[1],
            code=asset,
            order_type=1,
            buy_sell=1,
            trade_type=3,
            quantity=set_quantity,
            price=set_price,
            order_num=""
        )

        return order_cms

    def sendit(self):
        order = self.order_spec_cms()
        self.spec.send_order_fo(**order)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    k = Kiwoom.instance()
    k.connect()

    c = CMS(k)
    c.get_pred()
    a = c.gen_asset()
    print(a)