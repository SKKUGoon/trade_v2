from models.model_config import *
from main.live_db_conn import *

import math

class CMS(IramModel):
    # CMS Starts at 15:00, day T.
    # CMS Ends at 09:00 day T+1.
    def __init__(self, token, strategy=31):
        super().__init__(strategy)
        self.strat_num = strategy
        self.token['token_number'] = token

        # Log
        loc = 'C:\Data\log'
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

    def get_asset(self, spec:OrderSpec):
        current = spec.tick_price_base()
        asset_call, asset_put = spec.gen_option_code(current)
        prediction = self.cms_asset.lower()
        action = self.cms_prediction

        if prediction == 'call' and action == 1:
            self.log.debug(f'Asset is {asset_call}. Uploaded to local DB')
            return asset_call
        elif prediction == 'put' and action == 1:
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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    k = Kiwoom.instance()
    k.connect()
    o = OrderSpec(k)
    k.connect()

    c = CMS()
    c.get_pred()
    a = c.get_asset(o)
    print(a)