from sklearn.svm import SVC

from data.DATA_2to7_update import *
from util.UTIL_data_convert import *
from util.UTIL_log import Logger

import pandas as pd
import numpy as np
import pickle
import datetime


class VanillaTradeSVM():
    data_path = r'D:\trade_db\fixed_time_strategy_data'
    model_path = r'D:\trade_db\fixed_time_strategy_model'
    today = datetime.datetime.now()

    def __init__(self, path_name:str):
        self.data_path = self.data_path + path_name
        self.model_path = self.model_path + path_name
        self.logger = Logger(r'D:\trade_db\log')
        self._set_models()

    def _set_models(self, box_const=1, kappa='rbf', g='scale', class_w=None):
        self.model1 = SVC(
            C=box_const, kernel=kappa, degree=3, gamma=g, coef0=0.0,
            shrinking=True, tol=0.001, cache_size=1000, class_weight=class_w,
            verbose=False, max_iter=-1, decision_function_shape='ovr'
        )  # Model For CO Return, and US Indices

        self.model2 = SVC(
            C=box_const, kernel=kappa, degree=3, gamma=g, coef0=0.0,
            shrinking=True, tol=0.001, cache_size=1000, class_weight=class_w,
            verbose=False, max_iter=-1, decision_function_shape='ovr'
        )  # Model For 0 ~ 1, 0 ~ 2 Return

        self.model3 = SVC(
            C=box_const, kernel=kappa, degree=3, gamma=g, coef0=0.0,
            shrinking=True, tol=0.001, cache_size=1000, class_weight=class_w,
            verbose=False, max_iter=-1, decision_function_shape='ovr'
        )  # Model that Combines Model 1 and Model 2

    def get_data_2to7(self, week=156):
        # Data update
        update_index_us()
        update_index_kor()
        idx_features = index_features(0.00042617672128044044, 20210503)
        update_opt_path(idx_features)
        opt_features = option_features()

        feat = gen_features(index_features=idx_features,
                            option_features=opt_features)

        y = gen_target(feat)
        s, f = set_train_period(self.today, week)

        self.x1 = idx_features.loc[(idx_features.index >= s)
                                   & (idx_features.index <= f)]
        self.x2 = opt_features.loc[(opt_features.index >= s)
                                   & (opt_features.index <= f)]
        self.y = y.loc[(y.index >= s) & (y.index <= f)]

    def fit_(self, train_week=156):
        self.get_data_2to7(week=train_week)

        self.model1.gamma = get_gamma(self.x1)
        self.model1.fit(self.x1, (self.y >= 0))
        self.logger.critical(['[2to7] >>> Model 1 Fitted'])

        self.model2.fit(self.x2, (self.y >= 0))
        self.logger.critical(['[2to7] >>> Model 2 Fitted'])

        c_scr1 = pd.DataFrame(
            self.model1.decision_function(self.x1),
            index = self.x1.index
        )
        c_scr2 = pd.DataFrame(
            self.model2.decision_function(self.x2),
            index = self.x2.index
        )
        # Combined SVM
        self.model3.fit(
            pd.concat([c_scr1, c_scr2], axis=1),
            (self.y >= 0)
        )
        self.logger.critical(['[2to7] >>> Model Double SVM Fitted'])

    def save_model(self, names=('tts_m1', 'tts_m2', 'tts_m3')):
        file = [self.model1, self.model2, self.model3]
        for n, model in zip(names, file):
            with open(self.model_path + '\\' + f'{n}.pkl', 'wb') as f:
                pickle.dump(model, f)
        return list(map(lambda x: self.model_path + '\\' + f'{x}.pkl', names))

if __name__ == '__main__':
    v = VanillaTradeSVM(r'\2to7')

    v.fit_()
    s = v.save_model()
