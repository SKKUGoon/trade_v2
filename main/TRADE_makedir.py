import os

def chk_dir_msg(msg):
    return f"[Directory Check] >>> {msg}"

def chk_dir(create=False):
    missing = False
    # Base Directory
    if not os.path.exists(r'D:\trade_db'):
        print(chk_dir_msg('Base Directory Missing'))
        missing = True
        _create_base_dir(exec=create)
    # Log
    if not os.path.exists(r'D:\trade_db\log'):
        print(chk_dir_msg('Trade Log Directory Missing'))
        missing = True
        _create_log_dir(exec=create)

    # Trade Data
    if not os.path.exists(r'D:\trade_db\fixed_time_strategy_data'):
        print(chk_dir_msg('Trade Data Directory Missing'))
        missing = True


    if not os.path.exists(r'D:\trade_db\fixed_time_strategy_model'):
        print(chk_dir_msg('Trade Model Directory Missing'))
        missing = True
        _create_trade_data_dir(exec=create)

    if missing is False:
        print(chk_dir_msg('All directories in place'))


def _create_log_dir(loc=r'D:\trade_db\log', exec=False):
    if exec and not os.path.exists(loc):
        os.makedirs(loc)


def _create_trade_data_dir(data_path = r'D:\trade_db\fixed_time_strategy_data',
                          model_path = r'D:\trade_db\fixed_time_strategy_model',
                          exec=False):
    for directory in [data_path, model_path]:
        if exec and not os.path.exists(directory):
            os.makedirs(directory)


def _create_base_dir(loc=r'D:\trade_db', exec=False):
    if exec and not os.path.exists(loc):
        os.makedirs(loc)