# KOA Studio's functions is called by dynamicCall
# to simplify dynamicCall functions, the arguments for dynamicCalls
# are produced here.

def comm_connect():
    res = "CommConnect()"
    return res, None


def get_connect_state():
    res = "GetConnectState()"
    return res, None


def get_login_info(val):
    res = "GetLoginInfo(QString)"
    return res, val


def koa_functions(val1, val2):
    res = "KOA_Functions(QString, Qstring)"
    return res, val1, val2


def set_input_value(id, value):
    res = "SetInputValue(QString, QString)"
    return res, id, value


def comm_rq_data(rq_name, tr_code, prev_next, screen_num):
    res = "CommRqData(QString, QString, int, QString)"
    return res, rq_name, tr_code, prev_next, screen_num


def get_repeat_cnt(tr_code, rq_name):
    res = "GetRepeatCnt(QString, QString)"
    return res, tr_code, rq_name


def get_comm_data(tr_code, rq_name, index, key):
    res = "GetCommData(QString, QString, int, QString)"
    return res, tr_code, rq_name, index, key


def comm_get_data(code, real_type, field_name, index, item_name):
    res = "CommGetData(QString, QString, QString, int, QString)"
    return res, code, real_type, field_name, index, item_name


def disconnect_real_data(scr_num):
    res = "DisconnectRealData(QString)"
    return res, scr_num


def get_comm_data_ex(tr_code, multi_data_name):
    res = "GetCommDataEx(QString, QString)"
    return res, tr_code, multi_data_name


def get_comm_real_data(tr_code, fid):
    res = "GetCommRealData(QString, int)"
    return res, tr_code, fid


def comm_kw_rq_data(arr_code, cont, code_count, flag, rq_name, scr_num):
    res = "CommKwRqData(QString, QBoolean, int, int, QString, QString)"
    return res, arr_code, cont, code_count, flag, rq_name, scr_num


def send_order_(rq_name, screen_num, account, order_type, code,
               quantity, price, trade_type, original_order_num):
    res = "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)"
    return res, [rq_name, screen_num, account, order_type, code, quantity, price, trade_type, original_order_num]


def send_order_fo_(rq_name, screen_num, account, code, order_type,
                   buy_sell, trade_type, quantity, price, order_num):
    res = """SendOrderFO(QString, QString, QString, QString, 
            int, QString, QString, int, QString, QString)"""
    return res, [rq_name, screen_num, account, code, order_type, buy_sell, trade_type, quantity, price, order_num]


def get_chejan_data(fid):
    res = "GetChejanData(int)"
    return res, fid


def get_code_list_by_market(market):
    res = "GetCodeListByMarket(QString)"
    return res, market


def set_real_reg(screen_num, tr_code, fid, override_type):
    res = "SetRealReg(QString, QString, QString, QString)"
    return res, screen_num, tr_code, fid, override_type


def set_real_remove(screen_num, tr_code):
    res = "SetRealRemove(QString, QString)"
    return res, screen_num, tr_code