from strategy.STRAT_two_to_seven import *


class FTFactory:
    def timing(self, db):
        return db.get_time()


if __name__ == '__main__':
    d = FTFactory()
    print(d.timing(FTTwoSeven()))