import configparser as cp


# TODO: Delete when project is finished
# Execute this when config file fails
cfg = cp.ConfigParser()
cfg['DEFAULT'] = {'main_db' : '175.114.94.22'}
cfg['MySQL'] = {
    'db_id' : 'iramtrade',
    'db_pwd' : 'TradeIram1972',
    'db_name' : 'iram'
}

with open('../main/config.ini', 'w') as file:
    cfg.write(file)

with open('../_util/config.ini', 'w') as file:
    cfg.write(file)

with open('../_workers/config.ini', 'w') as file:
    cfg.write(file)

with open('../_workers_v2/config.ini', 'w') as file:
    cfg.write(file)

with open('../models/config.ini', 'w') as file:
    cfg.write(file)