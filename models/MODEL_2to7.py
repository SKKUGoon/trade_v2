from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler

from util.UTIL_data_convert import *

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
        x1 = pd.read_csv(self.data_path + r'\index_features.csv', index_col=0)
        x2 = pd.read_csv(self.data_path + r'\open_return_features.csv', index_col=0)

        y = pd.read_csv(self.data_path + r'\open_return_2_7_put.csv', index_col=0)
        s, f = set_train_period(self.today, week)

        self.x1 = x1.loc[(x1.index >= s) & (x1.index <= f)]
        self.x2 = x2.loc[(x2.index >= s) & (x2.index <= f)]
        self.y = y.loc[(y.index >= s) & (y.index <= f)]

    def fit_(self, train_week=156):
        self.get_data_2to7(week=train_week)

        self.model1.gamma = get_gamma(self.x1)
        self.model1.fit(self.x1, (self.y >= 0))

        self.model2.fit(self.x2, (self.y >= 0))

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
