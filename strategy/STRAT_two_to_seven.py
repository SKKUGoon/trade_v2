from strategy.__init__ import FTManager


class FTTwoSeven(FTManager):
    def get_time(self):
        time = {
            'buy' : '090200',
            'sell' : '090700',
            'standard' : '090010'
        }
        return time


class FTFactory:
    def timing(self, db):
        return db.get_time()