from util.UTIL_dbms import MySQLDBMethod
from typing import List

import datetime


iram = MySQLDBMethod(None, 'main')
def get_exception_date(exception) -> List:
    poss = {'1stBusinessDay', 'MaturityDay', 'SAT'}
    assert exception in poss, 'Check the type of exception'
    col = iram.get_column_list('ftsdc')

    cond = f"type='{exception}'"
    res = iram.select_db(target_table='ftsdc',
                         target_column=col,
                         condition=cond)
    return [val for ty, val in res]

# Strikes every 2nd Thursday
# if Thursday is holiday:
# Offering is moved to earlier dates.
def _date_to_alph(date_obj: datetime.datetime, bfaf:str):
    """
    :param date_obj:
    :param bfaf: signals whether we passed MaturityDay
        - if we did not pass it 'before'
        - if we pass it 'after'
    :return:
    """
    # TODO: Check if it's 2nd Thursday.
    alph_year = '6789012345ABCDEFGHJKLMNPQRSTVW'
    base_year = 1996
    alpha_month = '123456789ABC'

    # year
    y = date_obj.year - base_year
    y = y % 30

    # month
    if bfaf == 'before':
        m = date_obj.month
        m = m % 12 - 1
    elif bfaf == 'after':
        m = date_obj.month
        m = m % 12
        if m == 0:
            y = y + 1
    else:
        raise ValueError(f"Check if {date_obj} is datetime\nand {bfaf} is str")

    return alph_year[y] + alpha_month[m]


def _option_code_info():
    code1 = {
        'futures': '1',
        'call_option': '2',
        'put_option': '3',
        'spread': '4'
    }

    code2 = {
        'KOSPI200': '01'
    }
    return code1, code2


def __get_nearest(value, ls, reverse):
    """
    ls is sorted list
    """
    if reverse is False:
        for target in ls:
            if target - value >= 0:
                return target
    else:
        ls = list(reversed(ls))
        for target in ls:
            if target - value <= 0:
                return target


def _option_index_info(index_price, type_, otm=0):
    """
    Find the nearest OTM from the index_price

    ex)
    When index is 341. The standard is set as 2.5
    for call option:
        - nearest upper value where the price is least unfavorable: 342.5 -> XXXXX342
    for put option:
        - nearest lower value where the price is least unfavorable: 340 -> XXXXX340

    :param index_price: Realtime index_price
    :param type_: call or put
    :param otm:
    :return:
    """
    real_end = [0, 2.5, 5, 7.5, 10]

    if type_ == 'call_option':
        index_end = index_price % 10
        end = __get_nearest(index_end, real_end, reverse=False)
        op_ind = (index_price // 10) * 10 + end
        return int(op_ind)
    elif type_ == 'put_option':
        index_end = index_price % 10
        end = __get_nearest(index_end, real_end, reverse=True)
        op_ind = (index_price // 10) * 10 + end
        return int(op_ind)


def asset_code_gen(index, type_, date_info: datetime.datetime, bfaf, asset='KOSPI200'):
    code = list()

    info1, info2 = _option_code_info()
    code.append(info1[type_])
    code.append(info2[asset])
    code.append(_date_to_alph(date_info, bfaf))
    code.append(str(_option_index_info(index, type_=type_)))

    return ''.join(_ for _ in code)
