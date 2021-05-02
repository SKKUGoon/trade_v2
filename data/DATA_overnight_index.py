from util.UTIL_dbms import MySQLDBMethod

from typing import List

import pandas as pd
import numpy as np

iram = MySQLDBMethod(None, 'main')

def get_us_index(start:str, ric:str, table='z_market_index_price_test'):
    col = ['days', 'code', 'open', 'close']
    cond = f"code = '{ric}' and days = '{start}'"
    res = iram.select_db(target_table=table,
                         target_column=col,
                         condition=cond)
    res_open, res_close = (res[0][col.index('open')],
                           res[0][col.index('close')])
    print(f'{ric} for days: {start}')
    return (res_close - res_open) / res_open