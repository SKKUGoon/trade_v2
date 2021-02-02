from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop
from PyQt5.QtWidgets import QApplication

from _util.dbms import *
from _code.status import ReturnCode, FidList, TRKeys, RealType
from _code.dcall_func import *
from _util.errors import *
from _util.chk_api_count import RequestCheck
from _util._log import *

import datetime


class Kiwoom(QAxWidget):
    debug_print = False

    __instance = None  # Singleton Pattern to keep the values of class instance

    index_val = list()
    bid_ask_val = dict()

    order_submit = dict()
    order_cancel = dict()
    order_execute = dict()


    @classmethod
    def __get_instance(cls):
        return cls.__instance

    @classmethod
    def instance(cls, *args, **kwargs):
        """
        Singleton method
        """
        cls.__instance = cls(*args, **kwargs)
        cls.instance = cls.__get_instance
        return cls.__instance

    def __init__(self):
        super().__init__()
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

        # Event asynchronous loop
        self.login_loop = None
        self.request_loop = None
        self.buy_order_loop = None
        self.condition_loop = None

        # Server
        self.server_stat = None

        # Are there more than one page
        self.prev_next = 0

        # logging class
        loc = 'C:\Data\log'
        self.log = Logger(path=loc, name='TR_log')

        # API Queue limitation
        self.request_chk = RequestCheck(logging=self.log)
        self.order_chk = RequestCheck(logging=self.log)

        # After-event process: function connection
        self.OnEventConnect.connect(self._event_connect)
        self.OnReceiveMsg.connect(self._receive_msg)
        self.OnReceiveTrData.connect(self._receive_tr_data)
        self.OnReceiveChejanData.connect(self._receive_tr_conclude_data)
        self.OnReceiveRealData.connect(self._receive_real_data)

    # IN CASE OF LOGIN #
    def connect(self):
        """
        Requesting "CommConnect" to Kiwoom API
        Start login_loop
        """
        if not self.connect_status:
            self.dynamicCall(*comm_connect())
            self.login_loop = QEventLoop()
            self.login_loop.exec_()

    @property
    def connect_status(self):
        """
        :return:
            0 : Not Connected
            1 : Connected
        """
        return self.dynamicCall(*get_connect_state())

    @property
    def account_num(self):
        acc = self._get_login_info('ACCNO').rstrip(";")
        return acc.split(";")

    def _get_login_info(self, value):
        if not self.connect_status:
            raise KiwoomConnectionError("Kiwoom server not connected")

        values = ['ACCOUNT_CNT', 'ACCNO', 'USER_ID', 'USER_NAME', 'GetServerGubun']
        if value == 'GetServerGubun':
            res = self._get_server_type
        else:
            res = self.dynamicCall(*get_login_info(value))
        return res

    def _get_password_info(self):
        self.dynamicCall(*koa_functions('ShowAccountWindow', ''))

    def _get_server_type(self):
        server_stat = self.dynamicCall(*koa_functions('GetServerGubun', ''))

        if server_stat == '1':
            res = 'Mock_Server'
        else:
            res = 'Real_Server'
        return server_stat

    # IN CASE OF ANY EVENT #
    def _event_connect(self, status):
        start = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        if status == 0:
            msg = f"T{start}: Connection Successful"
        else:
            error = getattr(ReturnCode, 'CAUSE').get(status)
            msg = f"T{start}: Connection Failed. {error}"
        self.log.debug(msg)

        # Async loop exit.
        try:
            self.login_loop.exit()
        except AttributeError:
            pass

    def _receive_msg(self, screen_num, rq_name, tr_code, msg):
        """
        Method for message after an event
        """
        # if hasattr(self, "order_response"):
        #     self.order_response.update({'msg': msg})

        self.log.debug(msg)

    def _receive_tr_data(self, screen_num, rq_name, tr_code, record, prev_next, **kwarg):
        # Order
        if "ORD" in tr_code:
            order_num = self._get_comm_data(tr_code, '', 0, '주문번호')
            # self.order_response.update({'order_num': order_num})

            try:
                self.buy_order_loop.exit()
            except AttributeError:
                pass
            return

        # Just normal Transaction
        # if hasattr(self, 'order_response'):
        #     delattr(self, 'order_response')

        data = self.__get_data(tr_code, rq_name)
        setattr(self, tr_code, data)

        if prev_next == '0' or prev_next == '':
            self.prev_next = 0
        else:
            self.prev_next = 2

        # TR loop exit
        try:
            self.request_loop.exit()
        except AttributeError:
            pass

        # logging
        t = datetime.datetime.now()
        event = {
            'Day': t.strftime('%Y-%m-%d'),
            'Time': t.strftime('%H:%M:%S.%f'),
            'Event': 'Receive TR Data',
            'Request': rq_name,
            'TR_code': tr_code
        }
        self.log.debug(event)

    def _receive_real_data(self, code, real_type, real_data):
        """
        :param code:
        :param real_type: KOA_Studio's Real type _ reference to
        :param real_data: data itself
        :return:
        """
        if real_type not in {'업종지수', '잔고', '주식체결', '주식시세', '옵션시세', '옵션호가잔량'}:
            return
        start = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        data = [code, start]

        rt = getattr(RealType, 'real_type').get(real_type)
        res = {k: v for k, v in zip(rt.values(), [[] for _ in range(len(rt))])}
        for fid in getattr(RealType, 'real_type').get(real_type):
            val = self._get_comm_real_data(real_type, fid)
            res[rt[fid]].append(val)
            # Clean data from '+' and '-'
            val = val.lstrip('+')
            val = val.lstrip('-')
            data.append(val)
        if real_type in {'옵션호가잔량'}:  # For more asset fix here:
            self.bid_ask_val[code] = tuple(data)  # Tuple is hashable
        elif real_type == '업종지수':
            self.index_val.append(tuple(data))
        elif real_type == '잔고':
            pass
        else:
            pass
            #raise NotImplementedError
        return res

    def _receive_tr_conclude_data(self, clf, item_count, fid_list):
        if clf != '0':  # clf == 0 means the order is established
            return

        order_stat = self._get_tr_conclude_data('913').strip()
        if order_stat == '접수':
            table = 'orders_submitted'
            fid_dic = getattr(FidList, 'SUBMITTED')
        elif order_stat == '체결':
            table = 'orders_executed'
            fid_dic = getattr(FidList, 'EXECUTED')
        elif order_stat == '확인':  # cancel order
            table = 'orders_cancelled'
            fid_dic = getattr(FidList, 'CANCELLED')
        else:
            table = None
            fid_dic = getattr(FidList, 'ALL')

        t = datetime.datetime.now()
        res = {
            'Day': t.strftime('%Y%m%d'),
            'Time': t.strftime('%H%M%S.%f')
        }

        fids = fid_list.split(';')
        for fid in fids:
            fid_name = fid_dic.get(fid)
            if fid_name is None:
                continue
            data = self._get_tr_conclude_data(fid).strip()
            res[fid_name] = data
        self.log.debug(res)

        # json to dict. Eventually to local db
        if table == 'orders_submitted':
            self.order_submit = res
        elif table == 'orders_executed':
            self.order_execute = res
        elif table == 'orders_cancelled':
            self.order_cancel = res

    # Transaction receive method #
    @u_accepts({'id': str})
    def set_input_value(self, id, value):
        self.dynamicCall(*set_input_value(id, value))

    @u_accepts({'rq_name': str, 'tr_code': str, 'prev_next': int, 'screen_num': str})
    def _comm_rq_data(self, rq_name, tr_code, prev_next, screen_num):
        """
        Send transaction request(TR)
        :return:
        If return == -200: boom
        """
        if not self.connect_status:
            raise KiwoomConnectionError("Kiwoom server not connected")

        # API Queue limitation
        self.request_chk.req_check()

        res = self.dynamicCall(*comm_rq_data(rq_name, tr_code, prev_next, screen_num))

        if res != 0:  # Successful only if 0
            t = datetime.datetime.now()
            err = getattr(ReturnCode, "CAUSE").get(res)
            self.log.error(f"{t} Comm Req Data {rq_name} Fail. CAUSE {err}")
            raise KiwoomRequestFailError(f"Returned {res} due to {err}")

        self.log.debug(f'{datetime.datetime.now()} Comm Req Data {rq_name}')
        self.request_loop = QEventLoop()
        self.request_loop.exec_()

    @u_accepts({'tr_code': str, 'rq_name': str})
    def _get_repeat_count(self, tr_code, rq_name):
        count = self.dynamicCall(*get_repeat_cnt(tr_code, rq_name))
        return count

    @u_accepts({'tr_code': str, 'rq_name': str, 'index': int, 'key': str})
    def _get_comm_data(self, tr_code, rq_name, index, key):
        # Parameter type check
        data = self.dynamicCall(*get_comm_data(tr_code, rq_name, index, key))
        return data

    @u_accepts({'tr_code': str, 'code': str, 'real_type': str,
                'field_name': str, 'index': int, 'item_name': str})
    def _comm_get_data(self, code, real_type, field_name, index, item_name):
        ret = self.dynamicCall(*comm_get_data(code, real_type, field_name, index, item_name))
        return ret.strip()

    @u_accepts({'tr_code': str, 'multi_data_name': str})
    def _get_comm_data_ex(self, tr_code, multi_data_name):
        # Parameter type check
        data = self.dynamicCall(*get_comm_data_ex(tr_code, multi_data_name))
        return data

    def _get_comm_real_data(self, tr_code, fid):
        val = self.dynamicCall(*get_comm_real_data(tr_code, fid))
        return val

    @u_accepts({'arr_code': str, 'cont': int, 'code_count': int,
                'flag': int, 'rq_name': str, 'scr_num': str})
    def _comm_kw_rq_data(self, arr_code, cont, code_count, flag, rq_name, scr_num):
        if not self.connect_status:
            raise KiwoomConnectionError("Kiwoom server not connected")

        # API Queue limitation
        self.request_chk.req_check()

        res = self.dynamicCall(
            *comm_kw_rq_data(arr_code, cont, code_count, flag, rq_name, scr_num)
        )

        if res != ReturnCode.OP_ERR_NONE:
            t = datetime.datetime.now()
            self.log.error(f'{t} Comm Kw Req Data {rq_name} Fail.')
            raise KiwoomRequestFailError(f"Returned {res}.")

        self.request_loop = QEventLoop()
        self.request_loop.exec_()

    # Order Method
    def send_order(self, rq_name, screen_num, account, order_type,
                   code, quantity, price, trade_type, original_order_num=""):
        if not self.connect_status:
            msg = "Server not connected"
            # self.order_response.update({"msg": msg})
            raise KiwoomConnectionError("Kiwoom server not connected")

        order_params = {
            "rqname": rq_name,
            "scrno": screen_num,
            "accno": account,
            "ordertype": order_type,
            "code": code,
            "qty": quantity,
            "price": price,
            "hogatype": trade_type,
            "originorderno": original_order_num,
        }

        # order response data
        # self.order_response = {
        #     "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        #     "orderNo": "",
        # }
        # self.order_response.update(order_params)

        # sendout order
        try:
            self.order_chk.req_check()
            res = self.dynamicCall(
                *send_order_(rq_name, screen_num, account, order_type, code,
                             quantity, price, trade_type, original_order_num)
            )

        except Exception as msg:
            # self.order_response.update({"msg": msg})
            raise KiwoomOrderFailError(f"ERROR: send_order() : {msg}")

        if res != 0:
            msg = getattr(ReturnCode, "CAUSE").get(res)
            # self.order_response.update({"msg": msg})
            raise KiwoomOrderFailError(f"ERROR: send_order() : {msg}")

        # eventReceiveTrData() or timeout
        self.buy_order_loop = QEventLoop()
        self.buy_order_loop.exec_()

    def send_order_fo(self, rq_name, screen_num, account, code, order_type,
                      buy_sell, trade_type, quantity, price, order_num):
        if not self.connect_status:
            msg = "Server not connected"
            # self.order_response.update({"msg": msg})
            raise KiwoomConnectionError("Kiwoom server not connected")

        order_param = {
            'rqname': rq_name,
            'scrno': screen_num,
            'accno': account,
            'code': code,
            'ordkind': order_type,
            'slbytp': buy_sell,
            'ordtp': trade_type,
            'qty': quantity,
            'price': price,
            'orgordno': order_num
        }

        # self.order_response = {
        #     "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        #     "orderNo": "",
        # }
        # self.order_response.update(order_param)

        try:
            self.order_chk.req_check()
            res = self.dynamicCall(
                *send_order_fo_(rq_name, screen_num, account, code, order_type,
                                buy_sell, trade_type, quantity, price, order_num)
            )
        except Exception as msg:
            # self.order_response.update({"msg" : msg})
            raise KiwoomOrderFailError(f"Error: send_order_fo() : {msg}")

        if res != 0:
            msg = getattr(ReturnCode, "CAUSE").get(res)
            raise KiwoomOrderFailError(f"Error: send_order_fo() : {msg}")

        # Execute Loop
        self.buy_order_loop = QEventLoop()
        self.buy_order_loop.exec_()

    def _get_tr_conclude_data(self, fid):
        data = self.dynamicCall(*get_chejan_data(fid))
        return data

    def __get_data(self, tr_code, rq_name):
        res = dict()
        if getattr(TRKeys, tr_code).get('멀티데이터', False):
            res['멀티데이터'] = self.__get_multi_data(tr_code, rq_name)
        if getattr(TRKeys, tr_code).get('싱글데이터', False):
            res['싱글데이터'] = self.__get_single_data(tr_code, rq_name)
        return res

    def __get_single_data(self, tr_code, rq_name):
        data = dict()

        keys = getattr(TRKeys, tr_code).get('싱글데이터')
        for key in keys:
            val = self._get_comm_data(tr_code, rq_name, 0, key)
            cond1 = key.endswith('호가')
            cond2 = key in getattr(TRKeys, 'NOSIGNKEY')

            if cond1 or cond2:
                val = val.lstrip('-')
                val = val.lstrip('+')  # write json
            data[key] = val
        return data

    def __get_multi_data(self, tr_code, rq_name):
        data = list()

        count = self._get_repeat_count(tr_code, rq_name)
        keys = getattr(TRKeys, tr_code).get("멀티데이터")

        for i in range(count):
            tmp = dict()
            for key in keys:
                val = self._get_comm_data(tr_code, rq_name, i, key)

                cond1 = key.endswith('호가')
                cond2 = key in getattr(TRKeys, 'NOSIGNKEY')
                if cond1 or cond2:
                    val = val.lstrip('-')
                    val = val.lstrip('+')
                tmp[key] = val
            data.append(tmp)
        return data

    def __get_market_code(self, market):
        if market not in ['0', '10', '3', '8', '50', '4', '5', '6', '9', '30']:
            raise ValueError(f'{market} is not a valid market id')
        code = self.dynamicCall(*get_code_list_by_market(market)).split(';')
        return code

    # Real time data search
    @u_accepts({'screen_num': str, 'tr_code': str, 'fid': str})
    def set_real_register(self, screen_num, asset_code, fid='9001;10', override_type=False):
        if not self.connect_status:
            raise KiwoomConnectionError("Kiwoom server not connected")

        opt_type = int(override_type)
        self.dynamicCall(*set_real_reg(screen_num, asset_code, fid, override_type))

    def set_real_remove(self, screen_num, asset_code):
        self.dynamicCall(*set_real_remove(screen_num, asset_code))


if __name__ == '__main__':
    pp = QApplication(sys.argv)
    k = Kiwoom.instance()
    k.connect()
    k._get_password_info()