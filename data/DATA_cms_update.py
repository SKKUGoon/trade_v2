from sklearn import svm
from util.UTIL_dbms import *
from util.UTIL_asset_code import get_exception_date
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import math


db = MySQLDBMethod(None, db='main')
date_format = '%Y%m%d'
fb = get_exception_date('1stBusinessDay')
sat = get_exception_date('SAT')
if datetime.now().strftime('%Y%m%d') in (sat):
    sat = True
    timeline = '16:00:00'
    path_timeline = ['16:31:00', '15:40:00']
    path_new = ['1631', '1632', '1633', '1634']
else:
    sat = False
    timeline = '15:00:00'
    path_timeline = ['15:31:00', '14:40:00']
    path_new = ['1531', '1532', '1533', '1534']

#########################
##### BASE FUNCTION #####
#########################

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


def gen_factor_loading(X, ref_num):
    X_demean = X.sub(X.mean())
    T = len(X_demean)
    Q = X_demean.transpose().dot(X_demean)/T
    Q_np = Q.to_numpy()
    D, V = np.linalg.eigh(Q_np)

    lbd = D
    lbd_sorted = np.sort(lbd)[::-1]
    order = list()
    for i in range(len(lbd_sorted)):
        order.append(np.where(lbd == lbd_sorted[i])[0].tolist()[0])

    vi = np.transpose(np.transpose(V)[order])
    FPCA_fl = np.matmul(X_demean, vi).to_numpy()

    FPCA_fl = pd.DataFrame(FPCA_fl).set_index(X_demean.index)

    eigv_ratio = lbd_sorted / sum(lbd_sorted)

    X_fl = FPCA_fl[range(ref_num)]

    return X_fl, vi


def gen_factor(X):
    X = X.sub(X.mean())
    Q = X.transpose() @ X
    eigvals, eigvecs = np.linalg.eigh(Q)
    eigvals_srtd = np.sort(eigvals)
    indsrt = np.argsort(eigvals)
    eigvals_rvsrtd = eigvals_srtd[::-1]
    indrvsrt = indsrt[::-1]
    eigvecs_rvsrtd = eigvecs[:, indrvsrt]

    return eigvecs_rvsrtd


def gen_cumul_rtn(price, start, end):
    cum_return = pd.DataFrame(index=price.index)
    for i in price.columns[start:end]:
        cum_return[i] = np.log(price[i]) - np.log(price[price.columns[start]])
    return cum_return


def gen_date_inf(actual):
    pd.set_option('mode.chained_assignment', None)
    date = pd.to_datetime(pd.DataFrame({'dates': actual.index.tolist()})['dates'], format=date_format)
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


def standardscale(X_train, X_test):
    X_train_norm = X_train/(X_train.std())
    X_test_norm = X_test/(X_train.std())
    X_np_train = X_train_norm.to_numpy()
    X_np_test = X_test_norm.to_numpy()

    return X_np_train, X_np_test

##########################
##### MODEL FUNCTION #####
##########################
# first_busi_days = import_1stBusi_days(datefrom='20210101')
# SAT_days = import_SAT_days(datefrom='20210101')
# maturity_days = import_maturity_days(datefrom='20210101')
# today = datetime.today().strftime(date_format)

###############
# DATA UPDATE #
###############
def import_past_data(where=r'D:/trade_db/fixed_time_strategy_data/cms/'):
    opt_path_call_past = pd.read_csv(f'{where}opt_path_call.csv', index_col=0)
    opt_path_call_past.columns = opt_path_call_past.columns.astype(int)

    opt_path_call_open_past = pd.read_csv(f'{where}opt_path_call_open.csv', index_col=0)
    opt_path_call_open_past.columns = opt_path_call_open_past.columns.astype(int)

    co_return_past = pd.read_csv(f'{where}co_return_call.csv', index_col=0)
    return opt_path_call_past, opt_path_call_open_past, co_return_past


def gen_update_days(opt_path_call_past):
    res = db.select_db(target_table='ftsdr',
                       target_column=['days'],
                       condition=f'code = "201" and days >= "20210101"',
                       order_by='days asc',
                       distinct=True)
    today = datetime.today().strftime(date_format)

    result = pd.DataFrame(res)
    recent_days = result.loc[result.index[
        result[0] >= str(opt_path_call_past.index[-1])
    ]][0].tolist()
    if today in recent_days:
        recent_days.remove(today)

    return recent_days


def import_close_index(recent_days):
    recent_close_index = pd.Series(index=recent_days)
    SAT_days = import_SAT_days(datefrom='20210101')
    for i in range(len(recent_days)):
        if recent_days[i] in SAT_days:
            res = db.select_db(target_table='ftsdr',
                               target_column=['days', 'open'],
                               condition=f'code = "201" and time = "16:00:00" and days = "{recent_days[i]}"')
        else:
            res = db.select_db(target_table='ftsdr',
                               target_column=['days', 'open'],
                               condition=f'code = "201" and time = "15:00:00" and days = "{recent_days[i]}"')
        recent_close_index.loc[res[0][0]] = res[0][1]

    return recent_close_index


def get_ATM(recent_close_index):
    close_index = recent_close_index.copy().dropna()
    ATM_candi_list = [round(a, 4) for a in np.arange(0, 500, 2.5)]
    ATM_call_list = list()
    ATM_put_list = list()
    for i in range(len(close_index)):
        ATM_call_list.append(min([ATM for ATM in ATM_candi_list
                                  if ATM > close_index[i]]))
        ATM_put_list.append(max([ATM for ATM in ATM_candi_list
                                 if ATM < close_index[i]]))

    option_ATM_df = pd.DataFrame(index=close_index.index,
                                 columns=['close_index', 'ATM_call', 'ATM_put'])
    option_ATM_df['close_index'] = close_index
    option_ATM_df['ATM_call'] = ATM_call_list
    option_ATM_df['ATM_put'] = ATM_put_list

    return option_ATM_df


def get_recent_opt_path(option_ATM_df):
    first_busi_days = import_1stBusi_days(datefrom='20210101')
    SAT_days = import_SAT_days(datefrom='20210101')
    maturity_days = import_maturity_days(datefrom='20210101')

    time_horizon = list()
    for h in [12, 13, 14, 15]:
        for m in range(60):
            if h * 100 + m > 1545:
                break
            time_horizon.append(str(h * 100 + m))

    recent_opt_path_call = pd.DataFrame(index=[int(a) for a in option_ATM_df.index],
                                        columns=time_horizon)
    asset_type = "CALL"

    for i in range(len(option_ATM_df)):
        days = option_ATM_df.index.tolist()[i]
        recent_maturity_days = import_maturity_days(datefrom=days)
        sprc = option_ATM_df.loc[days]['ATM_call']
        cmon = int(recent_maturity_days[0][4:6])
        asset = f'201R{cmon}{math.floor(sprc)}'
        print(f'{days}: {asset}')

        if days in maturity_days:
            recent_opt_path_call.loc[int(days)] = [None] * len(recent_opt_path_call.columns)
        else:
            if days in SAT_days:
                opt_prc = db.select_db(target_table='ftsdr',
                                       target_column=['time', 'open'],
                                       condition=f'days="{days}" and code = "{asset}" and time >= "13:00:00" and time < "16:46:00"',
                                       order_by='time desc',
                                       limit=226)
                opt_prc_df_tem = pd.DataFrame(opt_prc, columns=['time', 'opt_open'])
                opt_prc_time = opt_prc_df_tem['time'].apply(lambda _: datetime.strptime(_, "%H:%M:%S")) + timedelta(
                    minutes=-60)
                opt_prc_time = opt_prc_time.apply(lambda _: _.strftime("%H%M"))
                opt_prc_df_tem['time'] = opt_prc_time.astype(str)

            else:
                opt_prc = db.select_db(target_table='ftsdr',
                                       target_column=['time', 'open'],
                                       condition=f'days="{days}" and code = "{asset}" and time >= "12:00:00" and time < "15:46:00"',
                                       order_by='time desc',
                                       limit=226)
                opt_prc_df_tem = pd.DataFrame(opt_prc, columns=['time', 'opt_open'])
                opt_prc_time = opt_prc_df_tem['time'].apply(lambda _: datetime.strptime(_, "%H:%M:%S")) + timedelta(
                    minutes=0)
                opt_prc_time = opt_prc_time.apply(lambda _: _.strftime("%H%M"))
                opt_prc_df_tem['time'] = opt_prc_time.astype(str)

            try:
                opt_prc_df_tem = opt_prc_df_tem.set_index(['time'], True)
                opt_prc_df = pd.DataFrame(opt_prc_df_tem, index=time_horizon)
                opt_prc_df = opt_prc_df.ffill(axis=0).bfill(axis=0)
                recent_opt_path_call.loc[int(days)] = opt_prc_df['opt_open'].tolist()
            except:
                pass

    recent_opt_path_call.columns = recent_opt_path_call.columns.astype(int)

    return recent_opt_path_call


def update_opt_path(opt_path_call_past, recent_opt_path_call):
    update_date = list(set(recent_opt_path_call.index) - set(opt_path_call_past.index))
    update_date.sort()
    opt_path_call = pd.concat([opt_path_call_past, recent_opt_path_call.loc[update_date]])

    return opt_path_call


def get_ATM_open(recent_close_index):
    today = datetime.today().strftime(date_format)

    close_index = recent_close_index.copy().dropna()
    ATM_candi_list = [round(a, 4) for a in np.arange(0, 500, 2.5)]
    ATM_call_list = list()
    ATM_put_list = list()
    for i in range(len(close_index)):
        ATM_call_list.append(min([ATM for ATM in ATM_candi_list if ATM > close_index[i]]))
        ATM_put_list.append(max([ATM for ATM in ATM_candi_list if ATM < close_index[i]]))

    option_ATM_df = pd.DataFrame(index=close_index.index, columns=['close_index', 'ATM_call', 'ATM_put'])
    option_ATM_df['close_index'] = close_index
    option_ATM_df['ATM_call'] = ATM_call_list
    option_ATM_df['ATM_put'] = ATM_put_list

    option_ATM_df.loc[today] = [None] * len(option_ATM_df.columns)
    option_ATM_df = option_ATM_df.shift(1)
    option_ATM_df = option_ATM_df.dropna()

    return option_ATM_df


def get_recent_opt_path_open(option_ATM_df_open):
    first_busi_days = import_1stBusi_days(datefrom='20210101')
    SAT_days = import_SAT_days(datefrom='20210101')
    maturity_days = import_maturity_days(datefrom='20210101')
    today = datetime.today().strftime(date_format)

    recent_opt_path_call_open = pd.DataFrame(index=[int(a) for a in option_ATM_df_open.index], columns=range(31))
    for i in range(len(option_ATM_df_open)):
        days = option_ATM_df_open.index.tolist()[i]
        sprc = option_ATM_df_open.loc[days]['ATM_call']
        recent_maturity_days = import_maturity_days(datefrom=str(int(days) - 1))
        cmon = int(recent_maturity_days[0][4:6])
        asset = f'201R{cmon}{math.floor(sprc)}'

        if days in SAT_days or days in first_busi_days:
            opt_prc = db.select_db(target_table='ftsdr',
                                   target_column=['time', 'open'],
                                   condition=f'days="{days}" and code = "{asset}" and time >= "10:00:00" and time < "10:31:00"',
                                   order_by='time_desc',
                                   limit=31)
            opt_prc_df_tem = pd.DataFrame(opt_prc, columns=['time', 'opt_open'])
            opt_prc_time = opt_prc_df_tem['time'].apply(lambda _: datetime.strptime(_, "%H:%M:%S"))
            opt_prc_time = opt_prc_time.apply(lambda _: _.strftime("%M"))
            opt_prc_df_tem['time'] = opt_prc_time.astype(str)
        else:
            opt_prc = db.select_db(target_table='ftsdr',
                                   target_column=['time', 'open'],
                                   condition=f'days="{days}" and code = "{asset}" and time >= "09:00:00" and time < "09:31:00"',
                                   order_by='time desc',
                                   limit=31)
            opt_prc_df_tem = pd.DataFrame(opt_prc, columns=['time', 'opt_open'])
            opt_prc_time = opt_prc_df_tem['time'].apply(lambda _: datetime.strptime(_, "%H:%M:%S"))
            opt_prc_time = opt_prc_time.apply(lambda _: _.strftime("%M"))
            opt_prc_df_tem['time'] = opt_prc_time.astype(int)
        try:
            opt_prc_df_tem = opt_prc_df_tem.set_index(['time'], True).sort_index()
            # Create Baseline
            baseline = pd.DataFrame(list(range(0, 31)))
            fit_base = pd.concat([opt_prc_df_tem, baseline],
                                 axis=1).ffill().bfill()
            fit_base = fit_base.set_index(fit_base[fit_base.columns[1]])
            fit_base.columns = ['opt_open', 'time']
            fit_base = fit_base.set_index('time', drop=True)
            opt_prc_df_tem = fit_base
            recent_opt_path_call_open.loc[int(days)] = opt_prc_df_tem['opt_open'].tolist()
        except:
            pass
    return recent_opt_path_call_open


def update_opt_path_open(opt_path_call_open_past, recent_opt_path_call_open):
    update_date_open = list(set(recent_opt_path_call_open.index) - set(opt_path_call_open_past.index))
    update_date_open.sort()
    opt_path_call_open = pd.concat([opt_path_call_open_past, recent_opt_path_call_open.loc[update_date_open]])
    return opt_path_call_open


def update_co_return(co_return_past, recent_opt_path_call, recent_opt_path_call_open):
    recent_opt_path_call = recent_opt_path_call.dropna()
    recent_opt_path_call_open.loc[recent_opt_path_call.index[0]] = [None] * len(recent_opt_path_call_open.columns)
    recent_opt_path_call_open = recent_opt_path_call_open.sort_index()
    recent_opt_path_call_open = recent_opt_path_call_open.shift(-1)
    recent_opt_path_call_open = recent_opt_path_call_open.loc[recent_opt_path_call.index]

    co_call_45_00 = (recent_opt_path_call_open[0].to_numpy() - recent_opt_path_call[1545].to_numpy()) / \
                    recent_opt_path_call[1545].to_numpy()
    co_call_45_01 = (recent_opt_path_call_open[1].to_numpy() - recent_opt_path_call[1545].to_numpy()) / \
                    recent_opt_path_call[1545].to_numpy()
    co_call_35_00 = (recent_opt_path_call_open[0].to_numpy() - recent_opt_path_call[1535].to_numpy()) / \
                    recent_opt_path_call[1535].to_numpy()
    co_call_35_01 = (recent_opt_path_call_open[1].to_numpy() - recent_opt_path_call[1535].to_numpy()) / \
                    recent_opt_path_call[1535].to_numpy()

    recent_co_return = pd.DataFrame(index=recent_opt_path_call.index)
    recent_co_return['co_call_45_00'] = co_call_45_00
    recent_co_return['co_call_45_01'] = co_call_45_01
    recent_co_return['co_call_35_00'] = co_call_35_00
    recent_co_return['co_call_35_01'] = co_call_35_01

    update_date_co = list(set(recent_co_return.index) - set(co_return_past.index))
    update_date_co.sort()
    co_return = pd.concat([co_return_past, recent_co_return.loc[update_date_co]])
    co_return = co_return.astype(float)

    return co_return


def cms_update_data():
    opt_path_call_past, opt_path_call_open_past, co_return_past = import_past_data()
    recent_days = gen_update_days(opt_path_call_past)
    recent_close_index = import_close_index(recent_days)

    option_ATM_df = get_ATM(recent_close_index)
    recent_opt_path_call = get_recent_opt_path(option_ATM_df)
    opt_path_call = update_opt_path(opt_path_call_past, recent_opt_path_call)

    option_ATM_df_open = get_ATM_open(recent_close_index)
    recent_opt_path_call_open = get_recent_opt_path_open(option_ATM_df_open)
    opt_path_call_open = update_opt_path_open(opt_path_call_open_past, recent_opt_path_call_open)

    co_return = update_co_return(co_return_past, recent_opt_path_call, recent_opt_path_call_open)

    opt_path_call.to_csv(r'D:/trade_db/fixed_time_strategy_data/opt_path_call.csv')
    opt_path_call_open.to_csv(r'D:/trade_db/fixed_time_strategy_data/opt_path_call_open.csv')
    co_return.to_csv(r'D:/trade_db/fixed_time_strategy_data/co_return_call.csv')

    return opt_path_call, opt_path_call_open, co_return

#######################
# TODAY DATA AND PRED #
#######################

def get_today_asset_code():
    today = datetime.today().strftime(date_format)
    res = db.select_db(target_table='ftsdr',
                       target_column=['days', 'open'],
                       condition=f'code = "201" and time = "{timeline}" and days = "{today}"')
    close_index_today = res[0][1]
    ATM_candi_list = [round(a, 4) for a in np.arange(0, 500, 2.5)]

    maturity_days = import_maturity_days(datefrom=today)
    sprc_call_today = min([ATM for ATM in ATM_candi_list if ATM > close_index_today])
    cmon = int(maturity_days[0][4:6])
    asset_call = f'201R{cmon}{int(math.floor(sprc_call_today))}'

    return asset_call


def get_today_path(asset_call, signal_window=55, price_31=2.90, price_32=2.93, price_33=2.98, price_34=2.90):
    today = datetime.today().strftime(date_format)
    time_horizon_today = list()
    for h in [14, 15]:
        for m in range(60):
            if h * 100 + m < 1440:
                continue
            if h * 100 + m > 1534:
                break
            time_horizon_today.append(str(h * 100 + m))

    opt_prc = db.select_db(target_table='ftsdr',
                           target_column=['time', 'open'],
                           condition=f'days="{today}" and time < "{path_timeline[0]}" and time >= "{path_timeline[1]}" and code = "{asset_call}"',
                           order_by='time desc',
                           limit=signal_window - 4)
    opt_prc_tem = pd.DataFrame(opt_prc, columns=['time', 'open'])
    opt_prc_time = opt_prc_tem['time'].apply(lambda _: datetime.strptime(_, "%H:%M:%S") + sat * timedelta(minutes=-60))
    opt_prc_time = opt_prc_time.apply(lambda _: datetime.strftime(_, "%H%M"))
    opt_prc_tem['time'] = opt_prc_time.astype(str)
    opt_prc_tem = opt_prc_tem.set_index(['time'], True)

    opt_prc_tem.loc[path_new[0]] = price_31
    opt_prc_tem.loc[path_new[1]] = price_32
    opt_prc_tem.loc[path_new[2]] = price_33
    opt_prc_tem.loc[path_new[3]] = price_34
    opt_prc_df_tem = pd.DataFrame(opt_prc_tem, index=time_horizon_today)
    opt_prc_df_tem = opt_prc_df_tem.ffill(axis=0).bfill(axis=0)
    opt_prc_df = pd.DataFrame(opt_prc_df_tem).iloc[range(0, signal_window, 1)].sort_index(ascending=True).reset_index(
        drop=True)

    return opt_prc_df


def gen_features(opt_path_call, opt_prc_today, signal_window=55):
    today = datetime.today().strftime(date_format)
    option_path_call = opt_path_call[opt_path_call.columns[range(160, 160 + signal_window, 1)]]
    option_path_call.columns = range(0, signal_window, 1)
    option_path_call.loc[int(today)] = opt_prc_today['open'].tolist()

    opt_path_call_raw = option_path_call.copy().astype(float)
    opt_path_call = gen_cumul_rtn(opt_path_call_raw, 0, signal_window)

    opt_path_call = opt_path_call.dropna()

    opt_path_call_fl, opt_path_call_f = gen_factor_loading(X=opt_path_call, ref_num=6)

    return opt_path_call_fl


def train_and_pred(opt_path_call_fl, co_return, train_window=104, bc_1st=1, cw_1st=None, train_window_2nd=10,
                   bc_2nd=12.6, ks_con_2nd=9.8, cw_2nd=None):
    today = datetime.today().strftime(date_format)
    co_return.loc[int(today)] = [None] * len(co_return.columns)
    y_call = co_return['co_call_35_00']
    date_inf = gen_date_inf(y_call)

    val_start = int(max(date_inf.weekth) - train_window_2nd)
    val_end = int(max(date_inf.weekth))
    prediction = pd.DataFrame(index=date_inf.index[(date_inf.weekth >= val_start) & (date_inf.weekth <= val_end)],
                              columns=['call_score'])
    for t in range(val_start, val_end + 1, 1):
        Y_call_train = y_call.loc[date_inf.index[(date_inf.weekth >= t - train_window) & (date_inf.weekth < t)]]
        X_call_train = opt_path_call_fl.loc[Y_call_train.index]
        X_call_test = opt_path_call_fl.loc[date_inf.index[date_inf.weekth == t]]

        Y_call_train_sign = np.sign(np.sign(Y_call_train) + 1)

        X_call_np_train, X_call_np_test = standardscale(X_call_train, X_call_test)

        clf = svm.SVC(C=bc_1st, class_weight=cw_1st, probability=True)
        clf.fit(X_call_np_train, Y_call_train_sign)
        pred = clf.predict(X_call_np_test).tolist()

        pred_score = clf.decision_function(X_call_np_test).tolist()
        prediction['call_score'].loc[X_call_test.index] = pred_score

    X_val = prediction.loc[date_inf.index[(date_inf.weekth >= val_start) & (date_inf.weekth < val_end)]]['call_score']
    X_val_np = np.array([[a] for a in X_val.to_list()])

    y_val = y_call.loc[date_inf.index[(date_inf.weekth >= val_start) & (date_inf.weekth < val_end)]]

    X_test = prediction.loc[date_inf.index[(date_inf.weekth == val_end)]]['call_score']
    X_test_np = np.array([[a] for a in X_test.to_list()])

    y_val_sign = np.sign(np.sign(y_val) + 1)
    X_var = X_val_np.var()

    ks = (1 / (X_var)) * (ks_con_2nd)

    clf = svm.SVC(C=bc_2nd, class_weight=cw_2nd, gamma=ks)
    clf.fit(X_val_np, y_val_sign)

    clf.predict(X_val_np)
    pred = clf.predict(X_test_np).tolist()
    score = clf.decision_function(X_test_np)

    today_pred = pd.DataFrame(pred, index=X_test.index).rename(columns={0: 'prediction'})
    today_score = pd.DataFrame(score, index=X_test.index).rename(columns={0: 'score'})
    today_pred = pd.concat([today_pred, today_score], axis=1)

    return today_pred


def cms_prediction(opt_path_call, co_return, p31_34=(2.90, 2.93, 2.98, 2.90)):
    asset_call = get_today_asset_code()
    opt_prc_today = get_today_path(asset_call, 55, *p31_34)
    opt_path_call_fl = gen_features(opt_path_call, opt_prc_today, signal_window=55)
    today_pred = train_and_pred(opt_path_call_fl, co_return, train_window=104, bc_1st=1, cw_1st=None,
                                train_window_2nd=10, bc_2nd=12.6, ks_con_2nd=9.8, cw_2nd=None)

    return today_pred

def cms_prediction_manual(opt_path_call, co_return, p31_34=(2.90, 2.93, 2.98, 2.90)):
    asset_call = get_today_asset_code()
    p31_34 = list()
    for i in range(4):
        a = float(input())
        p31_34.append(a)
    opt_prc_today = get_today_path(asset_call, 55, *p31_34)
    opt_path_call_fl = gen_features(opt_path_call, opt_prc_today, signal_window=55)
    today_pred = train_and_pred(opt_path_call_fl, co_return, train_window=104, bc_1st=1, cw_1st=None,
                                train_window_2nd=10, bc_2nd=12.6, ks_con_2nd=9.8, cw_2nd=None)

    return today_pred

if __name__ == '__main__':
    opt_path_call, opt_path_call_open, co_return = cms_update_data()
    asset_call = get_today_asset_code()
    today_pred = cms_prediction(opt_path_call, co_return)
    print(today_pred)

# asset_call = get_today_asset_code()
# opt_prc_today = get_today_path(asset_call)