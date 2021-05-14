from strategy.__init__ import FTManager
from util.UTIL_asset_code import get_exception_date

import datetime

class FTZeroThirtyFour(FTManager):

    def get_state(self):
        sat = get_exception_date('SAT')
        fb = get_exception_date('1stBusinessDay')

        today = datetime.datetime.now().strftime('%Y%m%d')
        if today in sat:
            state = ['155900', '160000']
            limit = ['160020']
            end = ['163400']

        else:
            state = ['145900', '150000']
            limit = ['150020']
            end = ['153400']

        return state, limit, end

    def my_name(self):
        return 'FTZeroThrityFour'