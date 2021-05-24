from strategy.__init__ import FTManager
from util.UTIL_asset_code import get_exception_date

import datetime


class FTCMSExt(FTManager):

    def get_state(self):
        sat = get_exception_date('SAT')
        fb = get_exception_date('1stBusinessDay')

        today = datetime.datetime.now().strftime('%Y%m%d')
        if (today in sat) or (today in fb):
            states = ['']
            limit = ['100005']
            end = ['095500', '100200']

        else:
            states = ['']
            limit = ['090005']
            end = ['085500', '090200']
        return states, limit, end

    def my_name(self):
        return 'FTCMSExt'
