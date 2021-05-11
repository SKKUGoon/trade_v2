from sklearn import svm

from util.UTIL_dbms import *

from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import math
import time


db = MySQLDBMethod(None, 'main')
def gen_factor(X):
    Q = X.transpose() @ X
    eigvals, eigvecs = np.linalg.eigh(Q)
    eigvals_srtd = np.sort(eigvals)
    indsrt = np.argsort(eigvals)
    eigvals_rvsrtd = eigvals_srtd[::-1]
    indrvsrt = indsrt[::-1]
    eigvecs_rvsrtd = eigvecs[:, indrvsrt]

    return eigvecs_rvsrtd

def gen_date_inf(actual):
    pd.set_option('mode.chained_assignment', None)
    date = pd.to_datetime(pd.DataFrame({'dates': actual.index.tolist()})['dates'], format='%Y%m%d')
    date_inf = pd.DataFrame()
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

def import_maturity_days(datefrom: str):
    cols_ftsdc = db.get_column_list(table_name='ftsdc')

    # 데이터를 업데이트의 날짜 가져오기 (10일)
    res = db.select_db(target_column=cols_ftsdc, target_table='ftsdc', condition=f'type = "MaturityDay" and code > "{datefrom}"')
    maturity_days = list()
    for i in range(len(res)):
        maturity_days.append(res[i][1])
    return maturity_days

def import_1stBusi_days(datefrom: str):
    cols_ftsdc = db.get_column_list(table_name='ftsdc')

    # 데이터를 업데이트의 날짜 가져오기 (10일)
    res = db.select_db(target_column=cols_ftsdc, target_table='ftsdc', condition=f'type = "1stBusinessDay" and code > "{datefrom}"')
    firstBusiness_Days = list()
    for i in range(len(res)):
        firstBusiness_Days.append(res[i][1])
    return firstBusiness_Days

def import_SAT_days(datefrom: str):
    cols_ftsdc = db.get_column_list(table_name='ftsdc')

    # 데이터를 업데이트의 날짜 가져오기 (10일)
    res = db.select_db(target_column=cols_ftsdc, target_table='ftsdc', condition=f'type = "SAT" and code > "{datefrom}"')
    SAT_days = list()
    for i in range(len(res)):
        SAT_days.append(res[i][1])
    return SAT_days


def update_opt_path(where=f'D:/trade_db/fixed_time_strategy_data/0to34/'):
    first_busi_days = import_1stBusi_days(datefrom='20160731')
    maturity_days = import_maturity_days(datefrom='20160731')
    SAT_days = import_SAT_days(datefrom='20160731')

    opt_path_call = pd.read_csv(where + 'opt_path_call_ATM1500.csv', index_col=0)
    opt_path_call_close = pd.read_csv(where + 'opt_path_call_close_ATM1500.csv', index_col=0)

    opt_path_call = opt_path_call.loc[opt_path_call.index > 20160731].dropna()
    opt_path_call_close = opt_path_call_close.loc[opt_path_call_close.index > 20160731].dropna()

    last = str(opt_path_call.index.tolist()[-1])
    today = datetime.today().strftime(format="%Y%m%d")

    res = db.select_db(target_table='ftsdr',
                       target_column=['days'],
                       condition=f'days > "{last}" and days < "{today}" and code = "201"',
                       distinct=True)
    if len(res) == 0:
        pass
    else:
        update_date = pd.DataFrame(res)[0].tolist()
        ATM_candi = [round(a, 3) for a in np.arange(0, 500, 2.5)]

        update_opt_path_call = pd.DataFrame(index=[int(a) for a in update_date], columns=opt_path_call.columns)
        update_opt_path_call_close = pd.DataFrame(index=[int(a) for a in update_date], columns=opt_path_call_close.columns)

        for d in update_date:
            SAT = 0
            ATM_time = "15:00:00"
            opt_time_end = "15:45:00"
            if d in SAT_days:
                SAT = 1
                ATM_time = (datetime.strptime(ATM_time, "%H:%M:%S") + timedelta(minutes=60)).strftime(format="%H:%M:%S")
                opt_time_end = (datetime.strptime(opt_time_end, "%H:%M:%S") + timedelta(minutes=60)).strftime(
                    format="%H:%M:%S")
            if d in maturity_days:
                continue
            if d in first_busi_days:
                continue
            res = db.select_db(target_table='ftsdr',
                               target_column=['open'],
                               condition=f'code = "201" and days = "{d}" and time = "{ATM_time}"')[0][0]
            ATM_call = min([ATM for ATM in ATM_candi if ATM >= res])
            recent_maturity_days = import_maturity_days(datefrom=d)
            cmon = int(recent_maturity_days[0][4:6])
            asset = f'201R{cmon}{math.floor(ATM_call)}'

            opt_prc = db.select_db(target_table='ftsdr',
                                   target_column=['time', 'open', 'close'],
                                   condition=f'days="{d}" and code = "{asset}" and time <= "{opt_time_end}"',
                                   order_by='time desc',
                                   )
            opt_prc_df_tem = pd.DataFrame(opt_prc, columns=['time', 'open', 'close'])
            opt_prc_time = opt_prc_df_tem['time'].apply(lambda _: datetime.strptime(_, "%H:%M:%S")) + timedelta(
                minutes=0 - SAT * 60)
            opt_prc_time = opt_prc_time.apply(lambda _: _.strftime("%H%M"))
            opt_prc_df_tem['time'] = opt_prc_time.astype(int).astype(str)
            opt_prc_df_tem = opt_prc_df_tem.set_index('time', drop=True)

            opt_prc_df = pd.DataFrame(opt_prc_df_tem, index=opt_path_call.columns)
            opt_prc_df = opt_prc_df.ffill(axis=0).bfill(axis=0)
            update_opt_path_call.loc[int(d)] = opt_prc_df['open'].tolist()
            update_opt_path_call_close.loc[int(d)] = opt_prc_df['close'].tolist()

        opt_path_call = pd.concat([opt_path_call, update_opt_path_call])
        opt_path_call_close = pd.concat([opt_path_call_close, update_opt_path_call_close])

        opt_path_call.to_csv(where + 'opt_path_call_ATM1500.csv')
        opt_path_call_close.to_csv(where + 'opt_path_call_close_ATM1500.csv')

    return opt_path_call, opt_path_call_close

def get_today_path(ATM_index=428.93, price_open_1459=2.71, price_close_1459=2.73):

    first_busi_days = import_1stBusi_days(datefrom='20160731')
    maturity_days = import_maturity_days(datefrom='20160731')
    SAT_days = import_SAT_days(datefrom='20160731')

    time_horizon = list()
    for h in [9, 10, 11, 12, 13, 14, 15]:
        for m in range(60):
            if h * 100 + m >= 1459:
                break
            time_horizon.append(str((h * 100 + m)))

    today = int(datetime.today().strftime(format="%Y%m%d"))
    today_path = pd.DataFrame(index=[today], columns=time_horizon)
    today_path_close = pd.DataFrame(index=[today], columns=time_horizon)

    assert today not in first_busi_days, print("first business day, no trade")
    assert today not in maturity_days, print("maturity day, no trade")

    SAT = 0
    opt_time_end = "14:59:00"
    if today in SAT_days:
        SAT = 1
        opt_time_end = (datetime.strptime(opt_time_end, "%H:%M:%S") + timedelta(minutes=60)).strftime(format="%H:%M:%S")

    ATM_candi = [round(a, 3) for a in np.arange(0, 500, 2.5)]

    ATM_call = min([ATM for ATM in ATM_candi if ATM >= ATM_index])
    recent_maturity_days = import_maturity_days(datefrom=today)
    cmon = int(recent_maturity_days[0][4:6])
    asset = f'201R{cmon}{math.floor(ATM_call)}'

    opt_prc = db.select_db(target_table='ftsdr',
                           target_column=['time', 'open', 'close'],
                           condition=f'days="{today}" and code = "{asset}" and time < "{opt_time_end}"',
                           order_by='time desc')

    opt_prc_df_tem = pd.DataFrame(opt_prc, columns=['time', 'open', 'close'])
    opt_prc_time = opt_prc_df_tem['time'].apply(lambda _: datetime.strptime(_, "%H:%M:%S")) + timedelta(
        minutes=0 - SAT * 60)
    opt_prc_time = opt_prc_time.apply(lambda _: _.strftime("%H%M"))
    opt_prc_df_tem['time'] = opt_prc_time.astype(int).astype(str)
    opt_prc_df_tem = opt_prc_df_tem.set_index('time', drop=True)

    opt_prc_df = pd.DataFrame(opt_prc_df_tem, index=time_horizon)
    opt_prc_df = opt_prc_df.ffill(axis=0).bfill(axis=0)

    today_path.loc[today] = opt_prc_df['open']
    today_path_close.loc[today] = opt_prc_df['close']

    today_path['1459'] = price_open_1459
    today_path_close['1459'] = price_close_1459

    today_path = today_path.astype(float)
    today_path_close = today_path.astype(float)
    return today_path, today_path_close


def get_9_15_signal(opt_path_call, opt_path_call_close):
    intraday_9_15_sg = list()
    for c in opt_path_call_close.columns:
        if int(c) >= 900 and int(c) < 1500:
            intraday_9_15_sg.append(str(c))

    opt_crtn_call = pd.DataFrame(index=opt_path_call_close.index, columns=intraday_9_15_sg)
    for c in opt_path_call_close.columns:
        opt_crtn_call[c] = np.log(opt_path_call_close[c]) - np.log(opt_path_call[intraday_9_15_sg[0]])

    X_9_15_call_opt = opt_crtn_call[intraday_9_15_sg]

    return X_9_15_call_opt

def get_12_15_signal(opt_path_call, opt_path_call_close):
    intraday_12_15_sg = list()
    for c in opt_path_call_close.columns:
        if int(c) >= 1200 and int(c) < 1500:
            intraday_12_15_sg.append(str(c))

    opt_crtn_call = pd.DataFrame(index=opt_path_call_close.index, columns=intraday_12_15_sg)
    for c in opt_path_call_close.columns:
        opt_crtn_call[c] = np.log(opt_path_call_close[c]) - np.log(opt_path_call[intraday_12_15_sg[0]])

    X_12_15_call_opt = opt_crtn_call[intraday_12_15_sg]

    return X_12_15_call_opt

def prediction(ATM_index, price_open_1459, price_close_1459, train_window=65, nf_9=6, nf_12=6):
    today = int(datetime.today().strftime(format="%Y%m%d"))

    opt_path_call, opt_path_call_close = update_opt_path()
    today_path, today_path_close = get_today_path(ATM_index, price_open_1459, price_close_1459)

    signal_list = opt_path_call.columns[opt_path_call.columns.astype(int) < 1500].tolist()

    X = pd.concat([opt_path_call[signal_list], today_path])
    X_close = pd.concat([opt_path_call_close[signal_list], today_path_close])

    X_9_15 = get_9_15_signal(X, X_close)
    X_12_15 = get_12_15_signal(X, X_close)

    Y_call = (opt_path_call['1534'] - opt_path_call['1500']) / opt_path_call['1500']
    Y_call.loc[today] = None

    date_inf = gen_date_inf(Y_call)

    today_week = date_inf.weekth[date_inf.index == today].tolist()[0]

    train_date = date_inf.index[(date_inf.weekth >= today_week - train_window) & (date_inf.weekth < today_week)]
    test_date = date_inf.index[date_inf.weekth == today_week]
    X_train_double = pd.DataFrame(index=train_date, columns=['9_15', '12_15'])
    X_test_double = pd.DataFrame(index=test_date, columns=['9_15', '12_15'])

    Y_train = (Y_call.loc[(date_inf.weekth >= today_week - train_window) & (date_inf.weekth < today_week)] > 0).astype(int)

    X_9_train = X_9_15.loc[(date_inf.weekth >= today_week - train_window) & (date_inf.weekth < today_week)]
    X_9_test = X_9_15.loc[(date_inf.weekth == today_week)]

    factor_9 = gen_factor(X_9_train)
    X_9_train_fl = X_9_train.dot(factor_9[:, 0:nf_9])
    X_9_test_fl = X_9_test.dot(factor_9[:, 0:nf_9])

    clf = svm.SVC(C=1, gamma='scale', kernel='rbf', class_weight=None)
    clf.fit(X_9_train_fl, Y_train)

    X_train_double['9_15'] = clf.decision_function(X_9_train_fl).tolist()
    X_test_double['9_15'] = clf.decision_function(X_9_test_fl).tolist()

    X_12_train = X_12_15.loc[(date_inf.weekth >= today_week - train_window) & (date_inf.weekth < today_week)]
    X_12_test = X_12_15.loc[(date_inf.weekth == today_week)]

    factor_12 = gen_factor(X_12_train)
    X_12_train_fl = X_12_train.dot(factor_12[:, 0:nf_12])
    X_12_test_fl = X_12_test.dot(factor_12[:, 0:nf_12])

    clf = svm.SVC(C=1, gamma='scale', kernel='rbf', class_weight=None)
    clf.fit(X_12_train_fl, Y_train)

    X_train_double['12_15'] = clf.decision_function(X_12_train_fl).tolist()
    X_test_double['12_15'] = clf.decision_function(X_12_test_fl).tolist()

    clf = svm.SVC(C=1, gamma='scale', kernel='rbf', class_weight=None)
    clf.fit(X_train_double, Y_train)

    pred_double = clf.predict(X_test_double)
    pred_double_score = clf.decision_function(X_test_double)

    prediction = pd.DataFrame(index=X_test_double.index, columns=['pred', 'pred_score'])
    prediction['pred'] = pred_double
    prediction['pred_score'] = pred_double_score

    return prediction

pred = prediction(ATM_index=428.93, price_open_1459=2.71, price_close_1459=2.73)

print(pred)