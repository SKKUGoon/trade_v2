from strategy.__init__ import FTManager
from util.UTIL_asset_code import get_exception_date

import datetime

class FTZeroThirtyFour(FTManager):

    def get_state(self):
        sat = get_exception_date('SAT')
        fb = get_exception_date('1stBusinessDay')

        today = datetime.datetime.now().strftime('%Y%m%d')
        if today in sat:
            state = ['']
            limit = ['']
            end = ['']

        else:
            state = ['']
            limit = ['']
            end = ['']

        return states, limit, end

    def my_name(self):
        return 'FTZeroThrityFour'