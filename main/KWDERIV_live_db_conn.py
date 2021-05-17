from code_.LOCALDB_table_col import TableColumns
from main.KWDERIV_order_spec import *

from PyQt5.QtCore import QTimer


class LiveDBCon:
    """
    class handles functions associated with DB connection.
    """
    __instance = None

    @classmethod
    def __get_instance(cls):
        return cls.__instance

    @classmethod
    def instance(cls, *args, **kwargs):
        cls.__instance = cls(*args, **kwargs)
        cls.instance = cls.__get_instance
        return cls.__instance

    def __init__(self, k:Kiwoom, termination=datetime.timedelta(hours=1),
                 strategy='CO', screen_num='0001'):
        # Kiwoom Api Connection

        self.k = k

        self.scr_num = screen_num
        self.start = datetime.datetime.now()
        self.termination = termination  # 2hours
        self.strategy = strategy

        # Local DB connection
        self.localdb = self.__create_local_db(table_name='RealTime_Index',
                                              content='index')
        self.localdb = self.__create_local_db(table_name='RT_Option',
                                              content='option')
        self.localdb = self.__create_local_db(table_name='RT_TR_S',
                                              content='transaction_subm')
        self.localdb = self.__create_local_db(table_name='RT_TR_E',
                                              content='transaction_exec')
        self.localdb = self.__create_local_db(table_name='RT_TR_C',
                                              content='transaction_cancel')
        self.localdb = self.__create_local_db(table_name='RT',
                                              content='time')

        # Log Connection
        loc = r'D:\trade_db\log'
        self.log = Logger(path=loc, name='Live_DB_log')

        self.local_db_qry = QTimer(self.k)
        self.local_db_qry.start(50 * 0.1)
        self.local_db_qry.timeout.connect(self.live_price_wrap)

        self.stop_cond = QTimer(self.k)
        self.stop_cond.start(1000 * 0.1)
        self.stop_cond.timeout.connect(self.real_remove_reg)

        self.condition_check = QTimer(self.k)
        self.condition_check.start(10000)
        self.condition_check.timeout.connect(
            lambda: self.log.debug(f"{datetime.datetime.now()} Connected")
        )

    def __create_local_db(self, table_name, content='option'):
        """
        :return:
            1. self.dbname
            2. self.order_type
            3. self.order_method
            4. (optional) self.position_type
            5. self.col
        """
        dbname = r'D:\trade_db\local_trade._db'
        localdb = LocalDBMethods2(dbname)
        localdb.conn.execute("PRAGMA journal_mode=WAL")  # To write ahead mode
        tc = TableColumns()
        if content == 'index':
            params = tc.col_index
            pk = list(params.keys()).index('code')
            localdb.create_table_w_pk(table_name=table_name,
                                      variables=params,
                                      pk_loc=pk)

        elif content == 'time':
            params = tc.col_time
            localdb.create_table(table_name=table_name,
                                 variables=params)
        elif content == 'option':
            params = tc.col_options
            pk = list(params.keys()).index('code')
            localdb.create_table_w_pk(table_name=table_name,
                                      variables=params,
                                      pk_loc=pk)
            count = localdb.count_rows(table_name)
            if count == 0:
                localdb.insert_rows(table_name,
                                    col_=list(params.keys()),
                                    rows_=[['0']*len(params)])  # One must insert something to update the value
        elif content == 'transaction_exec':
            params = tc.order_exec
            pk = list(params.keys()).index('SCREEN_NUM')
            localdb.create_table_w_pk(table_name=table_name,
                                      variables=params,
                                      pk_loc=pk)
            count = localdb.count_rows(table_name)
            if count == 0:
                localdb.insert_rows(table_name,
                                    col_=list(params.keys()),
                                    rows_=[['0']*len(params)])
        elif content == 'transaction_subm':
            params = tc.order_subm
            pk = list(params.keys()).index('SCREEN_NUM')
            localdb.create_table_w_pk(table_name=table_name,
                                      variables=params,
                                      pk_loc=pk)
            count = localdb.count_rows(table_name)
            if count == 0:
                localdb.insert_rows(table_name,
                                    col_=list(params.keys()),
                                    rows_=[['0']*len(params)])
        elif content == 'transaction_cancel':
            params = tc.order_cancel
            pk = list(params.keys()).index('SCREEN_NUM')
            localdb.create_table_w_pk(table_name=table_name,
                                      variables=params,
                                      pk_loc=pk)
            count = localdb.count_rows(table_name)
            if count == 0:
                localdb.insert_rows(table_name,
                                    col_=list(params.keys()),
                                    rows_=[['0']*len(params)])
        return localdb

    def _index_p_to_local(self, table='RealTime_Index'):
        if len(self.k.index_val) <= 1:
            for values in self.k.index_val.values():
                col = self.localdb.get_column_list(table)
                self.localdb.update_rows(table, col, [values])
                self.localdb.insert_database(table, col, [values],
                                             'upsert', key='code')

        elif len(self.k.index_val) > 1:
            for key, values in self.k.index_val.items():
                col = self.localdb.get_column_list(table)
                self.localdb.insert_database(table, col, [values],
                                             'upsert', key='code')


    # Live option price related methods
    def req_opt_price(self, asset, cols='10'):
        self.k.set_real_register(self.scr_num, asset, cols, 1)
        self.log.debug(f'{asset} real data stream requested')

    def _opt_p_to_local(self, table='RT_Option'):
        if len(self.k.bid_ask_val) <= 1:
            for values in self.k.bid_ask_val.values():  #
                col = self.localdb.get_column_list(table)

                self.localdb.update_rows(table, col, [values])
        elif len(self.k.bid_ask_val) > 1:
            for key, values in self.k.bid_ask_val.items():
                col = self.localdb.get_column_list(table)

                self.localdb.insert_database(table, col, [values],
                                             'upsert', key='code')

    # Transaction Complete related Method
    def _tr_to_local(self, table=('RT_TR_S', 'RT_TR_E', 'RT_TR_C')):

        values = [list(self.k.order_submit.values()),
                  list(self.k.order_execute.values()),
                  list(self.k.order_cancel.values())]
        values = [self.k.order_submit,
                  self.k.order_execute,
                  self.k.order_cancel]
        today = datetime.datetime.now().strftime('%Y%m%d')
        for t, dict_val in zip(table, values):
            if len(dict_val) != 0:
                self.localdb.insert_database(t,
                                             list(dict_val.keys()),
                                             [list(dict_val.values())],
                                             'upsert',
                                             key='SCREEN_NUM')
                # self.localdb.update_table_fromdict(t, dict_val)

        else:
            pass

    def _time_to_local(self, table='RT'):
        val = self.localdb.select_db(target_column=['*'],
                                     target_table=table)

        if len(self.k.servertime) > 0:
            if len(val) == 0:
                self.localdb.insert_rows(table_name=table,
                                         col_=['time'],
                                         rows_=[[self.k.servertime['servertime']]])
            else:
                self.localdb.update_rows(table_name=table,
                                         set_ls=['time'],
                                         set_val=[[self.k.servertime['servertime']]])

    # Wrapper for uploading
    def live_price_wrap(self, needs=(True, True, True)):
        self._time_to_local()
        if needs[0] is True:
            self._index_p_to_local()
        if needs[1] is True:
            self._opt_p_to_local()
        if needs[2] is True:
            self._tr_to_local()

    def real_remove_reg(self):
        """
        Enforce set real reg to work only for "self.termination"
        """
        time_cond = (
                datetime.datetime.now() >= self.start + self.termination
        )
        if time_cond:
            self.k.set_real_remove('ALL', 'ALL')

            self.log.debug(f'{datetime.datetime.now()} Real Data Stream Halted')
        else:
            pass


if __name__ == '__main__':
    app = QApplication(sys.argv)
    k = Kiwoom.instance()
    k.connect()
    t = LiveDBCon(k)
    t.req_opt_price(asset='201R5432', cols='10')
    t.req_opt_price(asset='201R5435', cols='10')
    app.exec()
