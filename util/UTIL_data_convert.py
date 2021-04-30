import pandas as pd
import datetime


def get_cumul_return(vector):
    result = list()
    for ele in vector:
        result.append((ele - vector[0]) / vector[0])

    return result


def set_train_period(today:datetime.datetime, train_weeks:int):
    day = {
        'Monday' : 3,
        'Tuesday' : 4,
        'Wednesday' : 5,
        'Thursday' : 6,
        'Friday' : 7
    }
    finish = (today
              - datetime.timedelta(day[today.strftime('%A')]))
    start = finish - datetime.timedelta(weeks=train_weeks)

    return list(map(lambda x: int(x.strftime('%Y%m%d')),
                    [start, finish]))


def get_gamma(feature:pd.DataFrame):
    return 1 / (feature.values.flatten().var() * len(feature.columns))