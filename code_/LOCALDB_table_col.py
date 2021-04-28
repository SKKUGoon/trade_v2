from typing import Dict
from code_.KW_status import *




class TableColumns:
    col_index = {
        'code' : 'Varchar(20)',
        'days' : 'Varchar(20)',
        'price' : 'Varchar(20)'
    }

    col_options = {
        'code' : 'Varchar(20)',
        'time' : 'Varchar(20)',
        'server_time': 'Varchar(20)',
        'p_current': 'Varchar(20)',
        'p_sell': 'Varchar(20)',
        'p_buy': 'Varchar(20)'
    }

    col_time = {
        'time' : 'Varchar(20)',
    }

    __fidlist_submit = getattr(FidList, 'SUBMITTED')
    __fidlist_execute = getattr(FidList, 'EXECUTED')
    __fidlist_cancel = getattr(FidList, 'CANCELLED')

    @staticmethod
    def _column_maker(dict_val: dict) -> Dict:
        target = dict_val.values()
        res = dict()
        res['Day'] = 'Varchar(20)'
        res['Time'] = 'Varchar(20)'
        for i in target:
            res[i] = 'Varchar(20)'

        return res

    @property
    def order_subm(self) -> Dict:
        return self._column_maker(self.__fidlist_submit)

    @property
    def order_exec(self) -> Dict:
        return self._column_maker(self.__fidlist_execute)

    @property
    def order_cancel(self) -> Dict:
        return self._column_maker(self.__fidlist_cancel)

if __name__ == '__main__':
    test = TableColumns()
    print(test.col_index)
    print(test.col_options)
    print(test.order_subm)