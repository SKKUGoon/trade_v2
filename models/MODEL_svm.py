from util.train_param import set_train_periods
from data_process.DATA_preprocess import *

from sklearn.metrics import confusion_matrix
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler

import pandas as pd
import numpy as np
import datetime


class VanilaSVM():
    def __init__(self, X:pd.DataFrame, y:pd.DataFrame):
        # Data
        self.X, self.y = X, y

        # Model
        self.model = None

    def drop_outliers(self, drop_dates:int):
        self.X = self.X.drop(index=drop_dates)

    def set_model(self, box_const=1, g='scale', kappa='rbf', class_w='balanced'):
        self.model = SVC(
            C=box_const, kernel=kappa, degree=3, gamma=g, coef0=0.0,
            shrinking=True, tol=0.001, cache_size=1000, class_weight=class_w,
            verbose=False, max_iter=-1, decision_function_shape='ovr'
        )


    def fit_predict(self, training_period:float, prediction_end, train_week=None,
                    dateformat='%Y%m%d', k_scale=1, prediction_start='20150101', scale=False):
        if self.model is None:
            raise RuntimeError('Set the model before fitting it')

        tdates = set_train_periods(str(prediction_end),
                                   period=training_period,
                                   weeks=train_week)


        # Data
        X = self.X.copy(True).dropna()
        y = self.y.copy(True)
        x_col, y_col = X.columns, y.columns

        dat = pd.concat([X, y], axis=1)

        self.prediction = pd.DataFrame(None)
        count = 0

        self.cscore_collect = pd.DataFrame(None)

        for start, finish in tdates:
            sta = int(start.strftime(dateformat))
            fin = int(finish.strftime(dateformat))

            sta2 = int((finish + datetime.timedelta(days=3)).strftime(dateformat))
            fin2 = int((finish + datetime.timedelta(days=7)).strftime(dateformat))

            if sta < int(prediction_start):
                pass
            else:
                train = dat.loc[(dat.index >= sta) & (dat.index <= fin)].dropna()
                test = dat.loc[(dat.index >= sta2) & (dat.index <= fin2)]
                X_train, y_train = train[x_col], train[y_col]
                X_test, y_test = test[x_col].dropna(), test[y_col]
                self.t1, self.t2 = X_train, y_train
                self.t3, self.t4 = X_test, y_test

                sc = StandardScaler(with_mean=False)
                sc.fit(X_train)
                if scale is True:
                    X_train = pd.DataFrame(sc.transform(X_train),
                                           columns=X_train.columns,
                                           index=X_train.index)

                self.model.gamma = get_gamma(X_train) * k_scale
                # print(get_gamma(X_train), self.model.gamma, get_gamma(X_train))
                self.model.fit(X_train,
                               y_train.replace(True, 1).replace(False, 0))

                cscore_collect = pd.DataFrame(
                    self.model.decision_function(X_train),
                    columns=['conf_scr'],
                    index=X_train.index
                )
                updt = [_ for _ in cscore_collect.index
                        if _ not in self.cscore_collect.index]
                updt_ind = list(map(lambda x: cscore_collect.index.tolist().index(x),
                                    updt))
                self.cscore_collect = pd.concat([self.cscore_collect,
                                                 cscore_collect.iloc[updt_ind, :]])

                if len(X_test) > 0:
                    if scale is True:
                        X_test = pd.DataFrame(sc.transform(X_test),
                                              columns=X_test.columns,
                                              index=X_test.index)
                    p1 = self.model.predict(X_test)
                    p2 = self.model.decision_function(X_test)

                    pred = pd.concat(
                        [pd.DataFrame(p1, columns=['actions'], index=X_test.index),
                         pd.DataFrame(p2, columns=['c_score'], index=X_test.index),
                         y_test],
                        axis=1
                    )
                    self.prediction = pd.concat([self.prediction, pred])
            count += 1
            print(f'Fitting Process >>> {round((count / len(tdates)) * 100, 2)}%',
                  end='\r')

    def cfs_matrix(self, real_value:str, pred_value:str):
        if self.prediction is None:
            raise RuntimeError('No Prediction to evaluate')
        self.prediction = self.prediction.replace(True, 1).replace(False, 0).dropna()
        self.cm = confusion_matrix(self.prediction[real_value],
                                   self.prediction[pred_value])

    def hitratio(self, type_:str):
        assert type_ in {'confusion', 'effective0', 'effective1', 'matrix'}

        if not hasattr(self, 'prediction'):
            raise AttributeError('No Confusion Matrix generated')
        self.cm = self.cm.transpose()
        if type_ == 'confusion':
            return np.sum(np.diag(self.cm)) / np.sum(self.cm)
        elif type_ == 'effective0':
            return self.cm[0][0] / np.sum(self.cm[0])
        elif type_ == 'effective1':
            return self.cm[1][1] / np.sum(self.cm[1])
        else:
            return self.cm
