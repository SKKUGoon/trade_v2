"""
Push this into IRAM git.
"""
from typing import List, Dict, Iterable

import sys

import pandas as pd
import sqlite3
import sqlalchemy

assert sys.version_info >= (3, 6), f'python version should be 3.6 or higher'


def process_config(configure, dbtype):
    """
    Insert config file to access the database
    :param configure: parsed configuration file
    :return: id, pw, db_ip, db_name as a tuple
    """
    default, personal = list(configure)
    main_db_access = configure[personal]

    if dbtype == 'main':
        id, pw = main_db_access['DB_ID'], main_db_access['DB_PWD']
        db_ip, db_name = configure[default]['Main_DB'], main_db_access['DB_NAME']

    else:
        id, pw = main_db_access['DB_ID'], main_db_access['DB_PWD']
        db_ip, db_name = configure[default]['Sub_DB'], main_db_access['DB_NAME']

    return id, pw, db_ip, db_name


def u_accepts(types):
    """
    Checks the type of instance that the function accepts.
    Checks only *args statement. Assume user can type *kwargs statement correctly.
    """
    assert isinstance(types, dict), f'types for u_accept must be dictionary'
    def check_accepts(f):

        def new_f(*args, **kwargs):
            """
            'new_f' takes arguments and keyword arguments from the decorated function.
            It first sort out the keyword arguments and use isinstance argument to check the type.
            Left over variables will be just arguments. And the function use isinstance again with arguments and types.values.
                ex) u_accepts({'variable_name' : type ...})
                    def f(variable_name: type ...):
                        ...
            """
            types_c = types.copy()
            for keywords in kwargs.keys():
                assert isinstance(kwargs[keywords], types_c[keywords]), f'kwarg {keywords} does not match {types_c[keywords]}'
                del types_c[keywords]

            for (a, t) in zip(args[1:], types_c.values()):
                assert isinstance(a, t), f'arg {a} does not match {t}'
            return f(*args, **kwargs)

        new_f.__name__ = f.__name__

        return new_f

    return check_accepts


def accepts(*types):
    """
    Checks the type of instance that the function accepts.
    Checks only *args statement. Assume user can type *kwargs statement correctly.
    """

    def check_accepts(f):
        assert len(types) == f.__code__.co_argcount - 1  # -1 because args include 'self'

        def new_f(*args, **kwargs):
            for (a, t) in zip(args[1:], types):  # [1:] because args include 'self' argument
                assert isinstance(a, t), f"arg {a} does not match {t}"
            return f(*args, **kwargs)

        new_f.__name__ = f.__name__
        return new_f

    return check_accepts


class LocalDBMethods2:
    """
    LocalDBMethods contains methods for
        1) getting table inside DB, getting columns from the table
        2) Creating table
        3) Inserting data
        4) Replacing data
        5) Updating data
    for both multiple rows and single rows.
    """

    def __init__(self, db_address):
        self.conn = self._create_connection(db_address)
        self.tick_table_list = {'INDEX': 'index_tick_fre_data', 'OPTION': 'option_tick_fre_data',
                                "STOCK": 'stock_tick_fre_data'}

    def __version__(self):
        return 'LocalDBMethods2 version 1.2.0a'

    def _execute_query(self, query: str, multiple: bool, new_vals=None):
        """
        :param query: Any str() query statement for SQL
        :param multiple: Boolean value that shows whether we add multiple rows or single rows.
        :param new_vals: If new_vals is not None, user would be replacing,inserting,updating the data
        """
        c = self.conn.cursor()
        if new_vals is None:
            c.execute(query)
            c.close()
        else:
            if multiple is True:
                assert len(new_vals) > 1, 'check if multiple'
                #c.execute('set max_allowed_packet=67108864')  # Override sql max_allowed_packet of 1MB
                c.executemany(query, new_vals)
                self.conn.commit()
                c.close()
            else:
                c.execute(query, new_vals[0])
                self.conn.commit()
                c.close()

    @u_accepts({'table_name': str, 'variables': Dict})
    def create_table(self, table_name: str, variables: dict):
        # Column and data types of columns is needed in dict
        new_cols = ', '.join(str(a) + ' ' + str(b)
                             for a, b in zip(variables.keys(), variables.values()))
        qry = f'create table if not exists {table_name} ({new_cols})'
        self._execute_query(qry, False)

    def create_table_w_pk(self, table_name: str, variables: dict, pk_loc:int):
        # Column and data types of columns is needed in dict
        assert pk_loc - 1 < len(variables), 'pk_loc out side of variables index'

        pk = list(variables.keys())[pk_loc]
        pk_val = variables[pk] + ' PRIMARY KEY'
        variables[pk] = pk_val

        new_cols = ', '.join(str(a) + ' ' + str(b)
                             for a, b in zip(variables.keys(), variables.values()))
        qry = f'create table if not exists {table_name} ({new_cols})'
        self._execute_query(qry, False)

    def _create_connection(self, db):
        conn = sqlite3.connect(db)
        return conn

    def _close_connection(self):
        self.conn.close()
        return 'connection ended'

    def get_table_list(self) -> List:
        c = self.conn.cursor()
        qry = "select name from sqlite_master where type='table' order by name"
        c.execute(qry)

        table_ls = c.fetchall()
        res = list()

        for table in table_ls:
            res.append(table[0])

        c.close()
        return res

    @u_accepts({'table_name': str})
    def get_column_list(self, table_name: str) -> List:
        c = self.conn.cursor()
        qry = f'PRAGMA table_info({table_name})'
        c.execute(qry)

        col_ls = c.fetchall()
        res = list()

        for columns in col_ls:
            res.append(columns[1])

        c.close()
        return res

    @u_accepts({'table_name': str, 'col_': Iterable, 'rows_': Iterable})
    def insert_rows(self, table_name: str, col_: Iterable, rows_: Iterable):
        # Multi, single combined
        columns = ', '.join(str(_) for _ in col_)
        rows = ', '.join('?' for _ in col_)
        qry = f'insert into {table_name} ({columns}) values ({rows})'

        # Execute
        multi_cond = (len(rows_) > 1)
        self._execute_query(qry, multi_cond, rows_)

    @u_accepts({'table_name': str, 'col_': Iterable, 'rows_': Iterable})
    def replace_rows(self, table_name: str, col_: Iterable, rows_: Iterable):
        # Separated from insert_rows method for user friendliness
        # Multi, single
        columns = ', '.join(str(_) for _ in col_)
        rows = ', '.join('?' for _ in col_)
        qry = f'replace into {table_name} ({columns}) values ({rows})'

        # Execute
        multi_cond = (len(rows_) > 1)
        self._execute_query(qry, multi_cond, rows_)

    #@u_accepts({'table_name': str, 'set_ls': Iterable, 'set_val': Iterable})
    def update_rows(self, table_name: str, set_ls: Iterable, set_val: Iterable, condition=None):
        """
        :condition: should be written in sql format.
             ex1) days = '20200909'
             ex2) days = '20200909' and days = '20200910'
             ex3) (condition1 and condition2) and (condition3 or condition4)
        """
        set_ = map(lambda x: str(x) + ' = ?', set_ls)
        set_list = ', '.join(str(_) for _ in set_)
        qry = f"update {table_name} set {set_list}"
        if condition is not None:
             qry = qry + f" where {condition}"
        else:
            pass

        # Execute
        self._execute_query(qry, False, set_val)

    def delete_rows(self, table_name: str, condition=None):
        qry = f"delete from {table_name}"
        if condition is not None:
            qry = qry + f" where {condition}"

        # Execute
        self._execute_query(qry, multiple=False)

    def delete_table(self, table_name):
        qry = f"drop table if exists {table_name}"
        # Execute
        self._execute_query(qry, multiple=False)

    def select_db(self, target_column: Iterable[str], target_table: str,
                  condition1:str=None, condition2:str=None):
        """
        Use select method of sql and import database into python environment
        :condition: should be written in sql format.
             ex1) days = '20200909'
             ex2) days = '20200909' and days = '20200910'
             ex3) (condition1 and condition2) and (condition3 or condition4)
        :condition2: takes conditions without where argument
        """
        col = ', '.join(str(cols) for cols in target_column)
        qry = f"SELECT {col} FROM {target_table}"

        if condition1 is not None:
            qry = qry + f' where {condition1}'
        else:
            pass

        if condition2 is not None:
            qry = qry + f' {condition2}'

        # Execute query
        c = self.conn.cursor()
        c.execute(qry)

        # Result
        res = c.fetchall()
        c.close()
        return res

    def count_rows(self, target_table):
        qry = f'SELECT COUNT(*) as cnt FROM {target_table}'
        # Execute query
        c = self.conn.cursor()
        c.execute(qry)

        # Result
        res = c.fetchall()
        c.close()
        return res[0][0]

    def insert_database(self, table_name: str, col_: Iterable, rows_: Iterable[Iterable],
                        condition='upsert', key=None):
        col_ls = ', '.join(str(_) for _ in col_)
        row_ls = ', '.join('?' for _ in col_)

        qry = f"insert into {table_name} ({col_ls}) values ({row_ls})"
        if condition == 'upsert':
            res = list()
            for col, row in zip(col_, rows_[0]):
                res.append(f"{col} = '{row}'")
            res = ', '.join(str(_) for _ in res)
            qry = f"{qry} on conflict({key}) do update set {res}"
        else:
            pass
        # Execute
        multi_cond = len(rows_) > 1
        self._execute_query(qry, multi_cond, rows_)

    # From dictionary Methods
    def create_table_fromdict(self, table_name:str, values:dict):
        # Does not insert the values
        new_coldict = values.keys()
        res = dict()
        for key in new_coldict:
            res[key] = 'Varchar(20)'

        new_col = ', '.join(f'{a} {b}' for a, b in res.items())
        qry = f'create table if not exists {table_name} ({new_col})'
        self._execute_query(qry, False)

    def insert_table_fromdict(self, table_name:str, new_val:dict):
        # Only single dict value can be inserted
        columns = ', '.join(str(_) for _ in new_val.keys())
        rows = ', '.join('?' for _ in new_val.items())
        qry = f'insert into {table_name} ({columns}) values ({rows})'

        new_val = list(new_val.values())
        # Execute
        self._execute_query(qry, False, [new_val])

    def update_table_fromdict(self, table_name:str, set_dict:dict, condition=None):
        set_ls = list(set_dict.keys())
        set_val = list(set_dict.values())
        set_ = map(lambda x: str(x) + ' = ?', set_ls)
        set_list = ', '.join(str(_) for _ in set_)
        qry = f"update {table_name} set {set_list}"
        if condition is not None:
            qry = qry + f" where {condition}"
        else:
            pass

        # Execute
        self._execute_query(qry, False, [set_val])


class MySQLDBMethod:
    """
    Class can
    1) Make connection to the SQL server Database
    2)
    """

    def __init__(self, configure, db, test=False):
        # Add module for additional security
        # Add connection designated for testing purpose
        # Read configuration file
        if db == 'main':
            # id, pw, db_ip, db_name = process_config(configure, dbtype=db)
            id, pw, db_ip, db_name = 'iramtrade', 'TradeIram1972', '210.92.27.104', 'iram'
            engine_command = f'mysql+mysqlconnector://{id}:{pw}@{db_ip}:3306/{db_name}'
            self.engine = sqlalchemy.create_engine(engine_command)
        else:
            id, pw, db_ip, db_name = process_config(configure, dbtype=db)
            engine_command = f'mysql+mysqlconnector://{id}:{pw}@{db_ip}:3306/{db_name}'
            self.engine = sqlalchemy.create_engine(engine_command)

        self.schema = db_name
        self.conn = self.engine.raw_connection()

        self.engine.connect()

    def __version__(self):
        return 'MySQL_db_method 1.2.0a'

    def _execute(self, query, multiple: bool, new_vals=None):
        """
        :param query: Any str() query statement for SQL
        :param multiple: Boolean value that shows whether we add multiple rows or single rows.
        :param new_vals: If new_vals is not None, user would be replacing,inserting,updating the data
        """
        c = self.conn.cursor()
        if new_vals is None:
            c.execute(query)
            c.close()
        else:
            if multiple is True:
                assert len(new_vals) > 1, 'check if multiple'
                c.executemany(query, new_vals)
                self.commit(enforce=True)
                c.close()
            else:
                c.execute(query, new_vals[0])
                self.commit()
                c.close()

    def commit(self, enforce=False):
        """
        Implement safe commit that needs additional verification.
        If one needs commit wihtout additional verification, one can change enforce=True
        :param enforce: If the enforce parameter is True, than it will not ask you whether to commit
        """
        if enforce is False:
            # Check commit
            print("Are you sure you want to change your data? y/n")
            ans = input()
            if ans == 'y':
                print("Change committed")
                self.conn.commit()
            elif ans == 'n':
                print("Change not committed")
            else:
                print('Answer must be either y or n')
        elif enforce is True:
            self.conn.commit()
        else:
            raise ValueError('Type of enforce parameter must be bool(True, False)')

    @u_accepts({'table_name': str, 'variables': Dict})
    def create_table(self, table_name: str, variables: Dict):
        new_cols = ', '.join(str(a) + ' '  + str(b)
                             for a, b in zip(variables.keys(), variables.values()))
        qry = f'create table if not exists {table_name} ({new_cols})'

        self._execute(qry, False)
        ...

    def create_from_dataframe(self, table_name: str, df: pd.DataFrame):
        """
        Generate sql database from pd.DataFrame by creating new table.
        """
        tgt = df.to_sql(name=table_name, con=self.engine.connect(), if_exists='fail')

    def get_table_list(self):
        qry = f"select table_name from information_schema.tables where table_schema = '{self.schema.lower()}'"

        c = self.conn.cursor()
        c.execute(qry)
        r = c.fetchall()

        res = list()
        for i in r:
            res.append(i[0])

        c.close()
        return res

    @u_accepts({'table_name': str})
    def get_column_list(self, table_name: str):
        qry = f'show columns from {table_name}'

        c = self.conn.cursor()
        c.execute(qry)
        r = c.fetchall()

        res = list()
        for i in r:
            res.append(i[0])

        c.close()
        return res

    @u_accepts({'table_name': str, 'col_': Iterable, 'rows_': Iterable})
    def insert_database(self, table_name: str, col_: Iterable, rows_: Iterable[Iterable],
                        condition=None):
        col_ls = ', '.join(str(_) for _ in col_)
        row_ls = ', '.join('%s' for _ in col_)

        qry = f"insert into {table_name} ({col_ls}) values ({row_ls})"
        if condition is not None:
            qry = qry + f' {condition}'

        # Execute
        multi_cond = len(rows_) > 1
        self._execute(qry, multi_cond, rows_)

    @u_accepts({'table_name': str, 'col_': Iterable, 'rows_': Iterable})
    def merge_into_database(self, table_name: str, col_: Iterable, rows_: Iterable[Iterable]):
        col_ls = ', '.join(str(_) for _ in col_)
        row_ls = ', '.join('%s' for _ in col_)

        merge_ = map(lambda x: f'{x} = values({x})', col_)
        merge_ls = ', '.join(str(_) for _ in merge_)

        qry = f"""insert into {table_name} ({col_ls}) values ({row_ls}) 
                  on duplicate key update {merge_ls}"""

        # Execute
        multi_cond = len(rows_) > 1
        self._execute(qry, multi_cond, rows_)

    @u_accepts({'table_name': str, 'condition': str})
    def delete_database(self, table_name: str, condition: str):
        qry = f"delete from {table_name} where {condition}"
        self._execute(qry, False)

    @u_accepts({'table_name': str, 'col_': Iterable, 'row_': Iterable})
    def replace_database(self, table_name: str, col_: Iterable, rows_: Iterable[Iterable]):
        col_ls = ', '.join(str(_) for _ in col_)
        rows = ', '.join('?' for _ in col_)

        qry = f"replace into {table_name} ({col_ls}) values ({rows})"

        # Execute
        multi_cond = len(rows_) > 1
        self._execute(qry, multi_cond, rows_)

    @u_accepts({'table_name': str, 'set_ls': Iterable, 'set_val': Iterable, 'condition': str})
    def update_database(self, table_name: str, set_ls: Iterable, set_val: Iterable[Iterable], condition: str):
        """
        SQL query should look like this;
            : UPDATE table_name SET var1 = desired value WHERE conditions;
        """
        set_ = map(lambda x: str(x) + ' = %s', set_ls)
        set_list = ', '.join(str(_) for _ in set_)

        qry = f"update {table_name} set {set_list} where {condition}"

        # Execute
        self._execute(qry, False, set_val)

    @u_accepts({'target_column': Iterable, 'target_table': str, 'condition': str})
    def select_db(self, target_column: Iterable[str], target_table: str, condition: str = None):
        """
        Use select method of sql and import database into python environment
        :condition: should be written in sql format.
             ex) days = '20200909'
        """
        # Make str() query
        col = ', '.join(str(cols) for cols in target_column)
        qry = f"SELECT {col} FROM {target_table}"

        if condition is not None:
            qry = qry + f' where {condition}'
        else:
            pass

        # Execute query
        c = self.conn.cursor()
        c.execute(qry)

        # Result
        res = c.fetchall()
        c.close()
        return res


    def add_primary(self, target_table: str, target_column: Iterable[str]):
        """
        Set primary key to particular columns in sql table.
        """
        col = ', '.join(str(cols) for cols in target_column)
        qry = f'ALTER TABLE {target_table} ADD PRIMARY KEY ({col})'

        print(f'query: {qry}')
        # Execute query
        c = self.conn.cursor()
        c.execute(qry)

if __name__ == '__main__':
    loc = r'C:\Data\local_trade_test._db'
    # test = LocalDBMethods2(loc)
    # var = {'testvar1':'Varchar(20)',
    #        'testvar2':'Varchar(30)'}
    # test.create_table_w_pk('testing',var, 1)
    test = MySQLDBMethod(None, 'main')