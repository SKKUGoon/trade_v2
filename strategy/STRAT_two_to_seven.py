from strategy.__init__ import FTManager
from util.UTIL_asset_code import get_exception_date

import datetime

class FTTwoSeven(FTManager):

    def get_state(self):
        sat = get_exception_date('SAT')
        fb = get_exception_date('1stBusinessDay')

        today = datetime.datetime.now().strftime('%Y%m%d')
        if (today in sat) or (today in fb):
            states = ['100100', '100200']
            limit = ['100120', '100120']

        else:
            states = ['090100', '090200']
            limit = ['090120', '090120']

        return states, limit

    def my_name(self):
        return 'FTTwoSeven'
