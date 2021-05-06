from strategy.__init__ import FTManager
from util.UTIL_asset_code import get_exception_date

import datetime

class FTCMS(FTManager):

    def get_state(self):
        sat = get_exception_date('SAT')
        fb = get_exception_date('1stBusinessDay')

        today = datetime.datetime.now().strftime('%Y%m%d')
        if (today in sat) or (today in fb):
            states = ['163100', '163200', '163300', '163400']
            limit = ['163158', '163258', '163358', '163420']
            end = ['']

        else:
            states = ['153100', '153200', '153300', '153400']
            limit = ['153158', '153258', '153358', '153420']
            end = ['']
        return states, limit, end

    def my_name(self):
        return 'FTCMS'

class FTCMSExt(FTManager):

    def get_state(self):
        sat = get_exception_date('SAT')
        fb = get_exception_date('1stBusinessDay')

        today = datetime.datetime.now().strftime('%Y%m%d')
