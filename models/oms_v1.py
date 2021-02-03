from models.model_config import *
from main.live_db_conn import *

import math

class OMS(IramModel):
    r = None
    # OMS Starts at 08:00, day T.
    # OMS Ends at 09:30 day T.

    def __init__(self, token, strategy=21):
        super().__init__(strategy)
        self.strat_num = strategy
        self.token['token_number'] = token
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

    @staticmethod
    def __old_db_oms_process(asset_res:List):
        call, put = asset_res
        if call[-1] == 1 and put[-1] == 0:
            return call
        elif (call[-1] == 1 and put[-1] == 1) or (call[-1] == 0 and put[-1] ==0):
            return None
        elif call[-1] == 0 and put[-1] == 1:
            return put

    def get_pred(self, table='omsr'):  # TODO: get table name from strategy itself
        """
        Starts at 08:30
        Must be end at 08:59
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

            except RetrieveNoneError:
                self.log.warning('Get_pred function returned None.')
                self.reconn_server()
            else:
                res = self.__old_db_oms_process(res)
                if res is not None:
                    for key, val in zip(col, res):
                        self.r[key] = val
                    self.log.debug(f"Trade Prediction for {self.strategy} fetched")
                if res is None:
                    self.r['days'] = datetime.datetime.now().strftime('%Y%m%d')
                    self.r['code'] = 'No Action'
                    self.r['version'] = ''
                    self.r['pre_corrected'] = 0
                break
        else:
            self.r = None  # If there is no prediction: self.r is None

    @property
    def oms_days(self):
        return self.r['days']

    @property
    def oms_asset(self):
        return self.r['code'].split('_')[0]

    @property
    def oms_version(self):
        return self.r['version']

    @property
    def oms_prediction(self):
        return self.r['pre_corrected']

    def get_asset(self, spec:OrderSpec):
        """
        Gets real closing price at 15:30
            - Fetch it from the
        """

        current = spec.tick_price_base()
        asset_call, asset_put = spec.gen_option_code(current)
        prediction = 'put'# TODO: original: self.oms_asset.lower()
        action = 1 # TODO: original: self.oms_prediction

        if prediction == 'call' and action == 1:
            self.log.debug(f'Asset is {asset_call}. Uploaded to local DB')
            return asset_call
        elif prediction == 'put' and action == 1:
            self.log.debug(f'Asset is {asset_put}. Uploaded to local DB')
            return asset_put
        else:
            # Terminate. No Transaction
            asset = 'N/A'
            self.log.warning(f"Prediction value is {prediction}.")
            return False


if __name__ == '__main__':
    app = QApplication(sys.argv)
    k = Kiwoom.instance()
    while True:
        try:
            k.connect()
        except Exception:
            print('KIWOOM FUCK YOU and FUCK YOUR SHIT SERVER')
            continue
        else:
            break
    o = OrderSpec(k)
    c = OMS()
    c.get_pred()
    print(c.get_asset(o))
