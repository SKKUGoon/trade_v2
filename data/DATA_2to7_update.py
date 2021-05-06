from util.UTIL_dbms import *
from util.UTIL_asset_code import get_exception_date

import pandas as pd
import numpy as np

from typing import List, Tuple
import datetime
import math

from sklearn import svm

db = MySQLDBMethod(None, 'main')
fb = get_exception_date('1stBusinessDay')
sat = get_exception_date('SAT')
if datetime.datetime.now().strftime('%Y%m%d') in (fb + sat):
    timeline = ['10:00:00', '10:31:00']
else:
    timeline = ['09:00:00', '09:31:00']


def import_maturity_days(start_date:str, equal:bool) -> List:
    cols_ftsdc = db.get_column_list(table_name='ftsdc')

    # 데이터를 업데이트의 날짜 가져오기 (10일)
    if equal is True:
        cond = f"type = 'MaturityDay' and code >= '{start_date}'"
    else:
        cond = f"type = 'MaturityDay' and code > '{start_date}'"
    res = db.select_db(target_column=cols_ftsdc,
                       target_table='ftsdc',
                       condition=cond)
    maturity_days = list()
    for i in range(len(res)):
        maturity_days.append(res[i][1])
    return maturity_days


def gen_date_inf(actual:pd.DataFrame) -> pd.DataFrame:
    pd.set_option('mode.chained_assignment', None)
    date = pd.to_datetime(
        pd.DataFrame({'dates': actual.index.tolist()})['dates'],
        format='%Y%m%d'
    )
    date_inf = pd.DataFrame(None)
    date_inf['date'] = date
    date_inf['weekday'] = date_inf.date.dt.weekday
    date_inf['month'] = date_inf.date.dt.month
    date_inf['monthth'] = pd.DataFrame(np.zeros(len(date)))
    date_inf['weekth'] = pd.DataFrame(np.zeros(len(date)))
    date_inf['dayth'] = pd.DataFrame(np.zeros(len(date)))

    months = 0
    weeks = 0
    days = 1
    for i in date_inf.index:
        if i == 0:
            continue
        if date_inf['weekday'][i] - date_inf['weekday'][i - 1] <= 0:
            weeks += 1
        if date_inf['month'][i] - date_inf['month'][i - 1] != 0:
            months += 1
        date_inf['monthth'][i] = int(months)
        date_inf['weekth'][i] = int(weeks)
        date_inf['dayth'][i] = int(days)
        days += 1
    date_inf.index = actual.index
    return date_inf


def update_index_us(loc:str=r'D:/trade_db/fixed_time_strategy_data/2to7/', date_format='%Y%m%d'):
    dow = pd.read_csv(loc + 'dow.csv', index_col=0).rename(
        columns={'close': 'dow_close', 'open': 'dow_open'}
    ).dropna()
    nasdaq = pd.read_csv(loc + 'nasdaq.csv', index_col=0).rename(
        columns={'close': 'nasdaq_close', 'open': 'nasdaq_open'}
    ).dropna()
    snp = pd.read_csv(loc + 'snp.csv', index_col=0).rename(
        columns={'close': 'snp_close', 'open': 'snp_open'}
    ).dropna()

    last = datetime.datetime.strptime(str(dow.index.tolist()[-1]),
                                      date_format)
    today = datetime.datetime.today()

    update_days = (today - last).days
    update = list()
    for i in range(update_days):
        update.append((last + datetime.timedelta(i + 1)).strftime(date_format))

    for d in update:
        res = db.select_db(target_table='z_market_index_price_test',
                           target_column=['open', 'close'],
                           condition=f'code = ".DJI" and days = "{d}"')
        result = pd.DataFrame(res, index=[int(d)], columns=['dow_open', 'dow_close'])
        dow = pd.concat([dow, result])

        res = db.select_db(target_table='z_market_index_price_test',
                           target_column=['open', 'close'],
                           condition=f'code = ".SPX" and days = "{d}"')
        result = pd.DataFrame(res, index=[int(d)], columns=['snp_open', 'snp_close'])
        snp = pd.concat([snp, result])

        res = db.select_db(target_table='z_market_index_price_test',
                           target_column=['open', 'close'],
                           condition=f'code = ".IXIC" and days = "{d}"')
        result = pd.DataFrame(res, index=[int(d)], columns=['nasdaq_open', 'nasdaq_close'])

        nasdaq = pd.concat([nasdaq, result])

    dow.to_csv(loc + 'dow.csv')
    nasdaq.to_csv(loc + 'nasdaq.csv')
    snp.to_csv(loc + 'snp.csv')


def update_index_kor(loc=r'D:/trade_db/fixed_time_strategy_data/2to7/kospi_omsd.csv'):
    kospi_tem = pd.read_csv(loc, index_col=0)
    kospi_tem = kospi_tem.dropna()

    last = datetime.datetime.strptime(str(kospi_tem.index.tolist()[-1]), "%Y%m%d")
    today = datetime.datetime.today()

    update_days = (today - last).days
    update = list()
    for i in range(update_days):
        update.append((last + datetime.timedelta(i + 1)).strftime("%Y%m%d"))

    col = ['class', 'code', 'open', 'close']
    for d in update:
        res = db.select_db(target_table='omsd',
                           target_column=col,
                           condition=f'code="KOR200I" and days ="{d}"')
        result = pd.DataFrame(res,
                              index=[int(d)],
                              columns=col)
        kospi_tem = pd.concat([kospi_tem, result])

    kospi_tem.to_csv(loc)


def get_co_ret_kospi(loc=r'D:/trade_db/fixed_time_strategy_data/2to7/kospi_omsd.csv'):
    kospi_tem = pd.read_csv(loc, index_col=0)
    kospi_tem = kospi_tem.dropna()

    kospi = pd.concat([kospi_tem['close'].shift(1),
                       kospi_tem['open']],
                      axis=1)
    kospi_co = (kospi['open'] - kospi['close']) / kospi['close']

    return kospi_co

def get_oc_ret_us(new_co:float, date:str, loc:str=r'D:/trade_db/fixed_time_strategy_data/2to7/') -> Tuple:
    dow = pd.read_csv(loc + 'dow.csv', index_col=0).rename(
        columns={'close': 'dow_close', 'open': 'dow_open'}
    )
    nasdaq = pd.read_csv(loc + 'nasdaq.csv', index_col=0).rename(
        columns={'close': 'nasdaq_close', 'open': 'nasdaq_open'}
    )
    snp = pd.read_csv(loc + 'snp.csv', index_col=0).rename(
        columns={'close': 'snp_close', 'open': 'snp_open'}
    )
    kospi_co = get_co_ret_kospi()
    kospi_co[date] = new_co # Today's CO Return

    weekend_date = [d for d in dow.index.tolist()
                    if datetime.datetime.strptime(str(d), "%Y%m%d").weekday() >= 5]

    dow = dow.drop(index=weekend_date)
    nasdaq = nasdaq.drop(index=weekend_date)
    snp = snp.drop(index=weekend_date)

    index_features_tem = pd.concat([dow.shift(1),
                                    nasdaq.shift(1),
                                    snp.shift(1),
                                    kospi_co], axis=1).rename(columns={0:'kospi_co'})

    dow_oc = pd.Series(index=index_features_tem.index)
    nasdaq_oc = pd.Series(index=index_features_tem.index)
    snp_oc = pd.Series(index=index_features_tem.index)

    nan_days = 0
    for d in range(1, len(index_features_tem)):
        if math.isnan(index_features_tem.iloc[d]['kospi_co']) is False:
            if (math.isnan(index_features_tem.iloc[d]['dow_close']) is True) and nan_days != 0:
                dow_oc.iloc[d] = (index_features_tem.iloc[d-1]['dow_close'] - index_features_tem.iloc[d-nan_days]['dow_open']) / \
                                 index_features_tem.iloc[d-nan_days]['dow_open']
                nasdaq_oc.iloc[d] = (index_features_tem.iloc[d-1]['nasdaq_close'] - index_features_tem.iloc[d-nan_days]['nasdaq_open']) / \
                                    index_features_tem.iloc[d-nan_days]['nasdaq_open']
                snp_oc.iloc[d] = (index_features_tem.iloc[d-1]['snp_close'] - index_features_tem.iloc[d-nan_days]['snp_open']) / \
                                 index_features_tem.iloc[d-nan_days]['snp_open']
                nan_days = 0

            else:
                dow_oc.iloc[d] = (index_features_tem.iloc[d]['dow_close'] - index_features_tem.iloc[d-nan_days]['dow_open']) / \
                                 index_features_tem.iloc[d-nan_days]['dow_open']
                nasdaq_oc.iloc[d] = (index_features_tem.iloc[d]['nasdaq_close'] - index_features_tem.iloc[d-nan_days]['nasdaq_open']) / \
                                    index_features_tem.iloc[d-nan_days]['nasdaq_open']
                snp_oc.iloc[d] = (index_features_tem.iloc[d]['snp_close'] - index_features_tem.iloc[d-nan_days]['snp_open']) / \
                                 index_features_tem.iloc[d-nan_days]['snp_open']
                nan_days = 0

        else:
            nan_days += 1

    return dow_oc, nasdaq_oc, snp_oc


def index_features(new_co_ret, date, loc_us=r'D:/trade_db/fixed_time_strategy_data/2to7/',
                   loc_kospi=r'D:/trade_db/fixed_time_strategy_data/2to7/kospi_omsd.csv'):
    dow_oc, nasdaq_oc, snp_oc = get_oc_ret_us(new_co_ret, date, loc=loc_us)
    kospi_co = get_co_ret_kospi(loc_kospi)
    kospi_co[date] = new_co_ret

    index_features = pd.concat([dow_oc, nasdaq_oc, snp_oc, kospi_co], axis=1)
    index_features.columns = ['dow_oc', 'nasdaq_oc', 'snp_oc', 'kospi_co']
    index_features = index_features.loc[index_features['kospi_co'].dropna().index]
    index_features = index_features.fillna(0)

    return index_features


def update_opt_path(idx_features, loc=r'D:/trade_db/fixed_time_strategy_data/2to7/opt_open_put.csv'):
    index_features = idx_features

    opt_open_put = pd.read_csv(loc, index_col=0)

    update_opt = list(set(index_features.index.tolist()) - set(opt_open_put.index.tolist()))

    ATM_candi_list = [round(a, 4) for a in np.arange(0, 500, 2.5)]

    opt_path_put_open_update = pd.DataFrame(index=update_opt, columns=range(31))
    for d in update_opt:
        res = db.select_db(target_table='ftsdr',
                           target_column=['open'],
                           condition=f'code = "201" and days = "{d}" and time = "{timeline[0]}"')[0][0]
        ATM_put = max([ATM for ATM in ATM_candi_list if ATM <= res])
        maturity_days = import_maturity_days(start_date=d, equal=True)
        cmon = int(maturity_days[0][4:6])
        asset = f"301R{cmon}{math.floor(ATM_put)}"

        opt_prc = db.select_db(target_table='ftsdr',
                               target_column=['time', 'open'],
                               condition=f'days="{d}" and code = "{asset}" and time >= "{timeline[0]}" and time < "{timeline[1]}"',
                               order_by='time desc',
                               limit=31)
        opt_prc_df_tem = pd.DataFrame(opt_prc, columns=['time', 'opt_open'])
        opt_prc_time = opt_prc_df_tem['time'].apply(lambda _: datetime.datetime.strptime(_, "%H:%M:%S"))
        opt_prc_time = opt_prc_time.apply(lambda _: _.strftime("%M"))
        opt_prc_df_tem['time'] = opt_prc_time.astype(str)

        opt_prc_df_tem = opt_prc_df_tem.set_index(['time'], True)
        opt_prc_df = pd.DataFrame(opt_prc_df_tem,
                                  index=[str(a) if len(str(a)) == 2 else "0" + str(a) for a in range(31)])
        opt_prc_df = opt_prc_df.ffill(axis=0).bfill(axis=0)
        opt_path_put_open_update.loc[d] = opt_prc_df['opt_open'].tolist()

    opt_path_put_open_update.columns = opt_path_put_open_update.columns.astype(str)
    opt_open_put = pd.concat([opt_open_put, opt_path_put_open_update])
    opt_open_put.to_csv(loc)


def option_features(loc=r'D:/trade_db/fixed_time_strategy_data/2to7/opt_open_put.csv'):
    opt_open_put = pd.read_csv(loc, index_col=0)

    open_return = pd.DataFrame(index=opt_open_put.index, columns=['open_0_1', 'open_0_2'])

    open_return['open_0_1'] = (opt_open_put['1'] - opt_open_put['0'])/opt_open_put['0']
    open_return['open_0_2'] = (opt_open_put['2'] - opt_open_put['0'])/opt_open_put['0']

    option_features = open_return

    return option_features


def gen_target(features):
    opt_open_put = pd.read_csv(r'D:/trade_db/fixed_time_strategy_data/2to7/opt_open_put.csv',
                               index_col=0)
    y = (opt_open_put['7'] - opt_open_put['2'])/opt_open_put['2']
    y = y.loc[features.index]
    return y


def gen_features(index_features, option_features):
    features = pd.concat([index_features, option_features], axis=1)
    features = features.dropna()
    return features


if __name__ == '__main__':
    ##### Made By Y #####
    ##### WEEKLY UPDATE #####op
    update_index_us()
    update_index_kor()  # Update Afterwards
    idx_features = index_features(0.00042617672128044044, 20210503)
    update_opt_path(idx_features)
    opt_features = option_features()
    feat = gen_features(index_features=idx_features,
                        option_features=opt_features)
    y = gen_target(feat)
